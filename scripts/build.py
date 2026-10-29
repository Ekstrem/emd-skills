#!/usr/bin/env python3
"""Сборка SKILL.md-артефактов из общих (common/) и языко-специфичных этапов.

Что делает:
  1. Читает конфиг языка `languages/<язык>/config.yaml`.
  2. Берёт порядок склейки из `scripts/stages.yaml`.
  3. Склеивает этапы в один markdown-файл с YAML-заголовком (frontmatter).
  4. Собирает пакет навыка (Claude Agent Skills / DSH): каталог
     `output/skills/<name>/` с `SKILL.md`-роутером и `references/*.md`, плюс
     `output/skills/<name>.zip` — форма «один каталог верхнего уровня с SKILL.md
     в корне», которую принимают Claude и DSH.

Запуск (нужен только Python 3.10+, PyYAML не требуется):
    python scripts/build.py                  # собрать все языки
    python scripts/build.py csharp           # собрать один язык
    python scripts/build.py csharp go        # несколько языков
    python scripts/build.py --check          # только проверка, без записи файлов
    python scripts/build.py --matrix         # матрица для GitHub Actions

`--matrix` печатает готовые для $GITHUB_OUTPUT строки:
    languages=[...]        все языки (для стратегии matrix джобы build)
    publishable=[...]      языки с `publish_repo` в конфиге
    has_publishable=true   есть ли что публиковать (пустая matrix ломает job)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
STAGES_FILE = SCRIPTS_DIR / "stages.yaml"
COMMON_DIR = ROOT / "common"
LANGUAGES_DIR = ROOT / "languages"
OUTPUT_DIR = ROOT / "output"
SKILLS_DIR = OUTPUT_DIR / "skills"

# Роутер навыка: файл с передним планом (name/description) и ссылками на этапы.
ROUTER_NAME = "skill.md"
# Каталог навыков DSH обрезает описание до 500 знаков — длиннее писать бессмысленно.
DESCRIPTION_MAX = 500

# Имя скилла: строчные латинские буквы, цифры и дефисы.
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# Плейсхолдеры сборки: {{language}}, {{build_command}} и т.п.
# `${{ ... }}` — это выражение GitHub Actions внутри примеров кода в этапах,
# его трогать нельзя, поэтому `$` перед скобками исключается.
PLACEHOLDER_RE = re.compile(r"(?<!\$)\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}")

REQUIRED_KEYS = ("name", "description", "output_file")
BLOCK_SCALARS = ("|", ">", "|-", ">-", "|+", ">+")


class BuildError(Exception):
    """Ошибка сборки: печатается без трейсбека, код возврата 1."""


# --------------------------------------------------------------------------
# Мини-парсер YAML (плоские конфиги)
# --------------------------------------------------------------------------

def _strip_comment(line: str) -> str:
    """Отрезает комментарий `#`, не трогая `#` внутри кавычек."""
    quote: str | None = None
    for index, char in enumerate(line):
        if quote is not None:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "#":
            return line[:index]
    return line


def _parse_scalar(raw: str, where: str) -> str:
    value = raw.strip()
    if not value:
        raise BuildError(f"{where}: пустое значение")
    if value[0] in "\"'":
        if len(value) < 2 or value[-1] != value[0]:
            raise BuildError(f"{where}: незакрытая кавычка в {value!r}")
        return value[1:-1]
    return value


def _parse_inline_list(raw: str, where: str) -> list[str]:
    body = raw.strip()
    if not (body.startswith("[") and body.endswith("]")):
        raise BuildError(f"{where}: ожидался список вида [a, b] или блок `- элемент`")
    inner = body[1:-1].strip()
    if not inner:
        return []
    return [_parse_scalar(part, where) for part in inner.split(",")]


def load_flat_yaml(path: Path) -> dict[str, object]:
    """Читает плоский YAML: `ключ: значение`, `ключ: [a, b]`, `ключ:` + `- элемент`.

    Полный YAML сознательно не поддерживается: он нужен только для плоских
    конфигов, а зависимость от PyYAML ломала бы сборку на чистой машине.
    Всё, что не вписывается в подмножество, отвергается с понятной ошибкой,
    чтобы опечатка не дала молчаливо неверный артефакт.
    """
    if not path.is_file():
        raise BuildError(f"не найден файл {path.relative_to(ROOT)}")

    data: dict[str, object] = {}
    current_key: str | None = None

    for lineno, raw_line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), 1
    ):
        line = _strip_comment(raw_line).rstrip()
        if not line.strip() or line.strip() == "---":
            continue
        where = f"{path.relative_to(ROOT)}:{lineno}"

        stripped = line.strip()
        if stripped.startswith("- "):
            if current_key is None or not isinstance(data.get(current_key), list):
                raise BuildError(f"{where}: элемент списка без ключа")
            data[current_key].append(_parse_scalar(stripped[2:], where))
            continue

        if ":" not in stripped:
            raise BuildError(f"{where}: ожидалось 'ключ: значение'")

        key, _, rest = stripped.partition(":")
        key = key.strip()
        rest = rest.strip()
        if not key:
            raise BuildError(f"{where}: пустой ключ")
        if key in data:
            raise BuildError(f"{where}: повторяющийся ключ '{key}'")

        if rest in BLOCK_SCALARS:
            raise BuildError(f"{where}: многострочные значения ('{rest}') не поддерживаются")
        if not rest:
            data[key] = []
        elif rest.startswith("["):
            data[key] = _parse_inline_list(rest, where)
        else:
            data[key] = _parse_scalar(rest, where)
        current_key = key

    return data


# --------------------------------------------------------------------------
# Загрузка конфигов
# --------------------------------------------------------------------------

def load_manifest() -> dict[str, list[str]]:
    manifest = load_flat_yaml(STAGES_FILE)
    for key, value in manifest.items():
        if not isinstance(value, list):
            raise BuildError(f"scripts/stages.yaml: '{key}' должен быть списком этапов")
    if not manifest.get("common"):
        raise BuildError("scripts/stages.yaml: пустой список 'common'")
    return manifest  # type: ignore[return-value]


def load_languages(manifest: dict[str, list[str]]) -> dict[str, dict[str, object]]:
    if not LANGUAGES_DIR.is_dir():
        raise BuildError("не найден каталог languages/")

    configs: dict[str, dict[str, object]] = {}
    for lang_dir in sorted(p for p in LANGUAGES_DIR.iterdir() if p.is_dir()):
        config_path = lang_dir / "config.yaml"
        if not config_path.is_file():
            print(
                f"ПРЕДУПРЕЖДЕНИЕ: пропускаю languages/{lang_dir.name} — нет config.yaml",
                file=sys.stderr,
            )
            continue
        configs[lang_dir.name] = load_flat_yaml(config_path)

    if not configs:
        raise BuildError("не найдено ни одного languages/*/config.yaml")
    return configs


# --------------------------------------------------------------------------
# Проверка и сборка
# --------------------------------------------------------------------------

def _check_unlisted(
    directory: Path, expected: list[str], manifest_key: str, exclude: set[str] | None = None
) -> None:
    actual = {path.stem for path in directory.glob("*.md")}
    actual -= exclude or set()
    missing = sorted(actual - set(expected))
    if missing:
        listed = ", ".join(f"{name}.md" for name in missing)
        raise BuildError(
            f"эти файлы не попадут в артефакт: {listed}. "
            f"Добавьте их в scripts/stages.yaml (ключ '{manifest_key}') или удалите."
        )


def stage_paths(slug: str, manifest: dict[str, list[str]]) -> list[str]:
    """Возвращает пути этапов в порядке склейки: сначала common, затем язык."""
    if slug not in manifest:
        raise BuildError(
            f"язык '{slug}' не описан в scripts/stages.yaml. "
            "Добавьте ключ с порядком этапов."
        )

    common_names = manifest["common"]
    lang_names = manifest[slug]
    if not lang_names:
        raise BuildError(f"scripts/stages.yaml: пустой список этапов для '{slug}'")

    if not COMMON_DIR.is_dir():
        raise BuildError("не найден каталог common/")
    if not (LANGUAGES_DIR / slug).is_dir():
        raise BuildError(f"не найден каталог languages/{slug}/")

    _check_unlisted(COMMON_DIR, common_names, "common")
    # skill.md — роутер пакета навыка, он не является этапом и в артефакт не клеится.
    _check_unlisted(LANGUAGES_DIR / slug, lang_names, slug, exclude={Path(ROUTER_NAME).stem})

    paths: list[str] = []
    for name in common_names:
        rel = f"common/{name}.md"
        if not (ROOT / rel).is_file():
            raise BuildError(f"scripts/stages.yaml: нет файла {rel}")
        paths.append(rel)
    for name in lang_names:
        rel = f"languages/{slug}/{name}.md"
        if not (ROOT / rel).is_file():
            raise BuildError(f"scripts/stages.yaml: нет файла {rel}")
        paths.append(rel)
    return paths


def _substitute(text: str, config: dict[str, object], where: str) -> str:
    """Подставляет {{ключ}} из config.yaml. Неизвестный плейсхолдер — ошибка.

    Выражения GitHub Actions (`${{ github.repository }}` и подобные) в примерах
    кода пропускаются как есть.
    """
    scalars = {key: value for key, value in config.items() if isinstance(value, str)}

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in scalars:
            known = ", ".join(sorted(scalars)) or "—"
            raise BuildError(
                f"{where}: неизвестный плейсхолдер {{{{{key}}}}}. Доступные ключи: {known}"
            )
        return scalars[key]

    return PLACEHOLDER_RE.sub(replace, text)


def _read_text(path: Path) -> str:
    """Читает файл как UTF-8 без BOM и с нормализованными переводами строк.

    Нормализация нужна, чтобы артефакт был побайтово одинаковым при локальной
    сборке на Windows (CRLF) и в CI на Linux (LF).
    """
    text = path.read_text(encoding="utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def build_text(
    slug: str, config: dict[str, object], manifest: dict[str, list[str]]
) -> tuple[str, list[str]]:
    for key in REQUIRED_KEYS:
        value = config.get(key)
        if not isinstance(value, str) or not value.strip():
            raise BuildError(
                f"languages/{slug}/config.yaml: обязательный ключ '{key}' не заполнен"
            )

    name = str(config["name"]).strip()
    description = " ".join(str(config["description"]).split())

    if not NAME_RE.match(name):
        raise BuildError(
            f"languages/{slug}/config.yaml: name '{name}' должен состоять из строчных "
            "латинских букв, цифр и дефисов (например, edm-go)"
        )
    if not description:
        raise BuildError(f"languages/{slug}/config.yaml: пустой description")

    output_file = str(config["output_file"]).strip()
    if Path(output_file).name != output_file or not output_file.endswith(".md"):
        raise BuildError(
            f"languages/{slug}/config.yaml: output_file должен быть именем .md-файла "
            f"без каталогов, получено '{output_file}'"
        )

    paths = stage_paths(slug, manifest)
    parts = [
        "---",
        f"name: {name}",
        f"description: {json.dumps(description, ensure_ascii=False)}",
        "---",
        "",
    ]
    for rel in paths:
        content = _read_text(ROOT / rel)
        content = _substitute(content, config, rel).strip("\n")
        if not content:
            raise BuildError(f"{rel}: пустой файл")
        parts.append(f"<!-- source: {rel} -->")
        parts.append("")
        parts.append(content)
        parts.append("")

    return "\n".join(parts).rstrip() + "\n", paths


def output_path(config: dict[str, object]) -> Path:
    return OUTPUT_DIR / str(config["output_file"])


# --------------------------------------------------------------------------
# Пакет навыка: каталог <name>/SKILL.md + references/*.md и его zip
# --------------------------------------------------------------------------

REFERENCE_RE = re.compile(r"references/([A-Za-z0-9._-]+\.md)")


def _read_frontmatter(path: Path, rel: str) -> tuple[dict[str, str], str]:
    """Возвращает (поля заголовка, тело) файла навыка."""
    text = _read_text(path)
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise BuildError(f"{rel}: нужен YAML-заголовок (frontmatter) в начале файла")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise BuildError(f"{rel}: заголовок не закрыт строкой '---'") from None

    data: dict[str, str] = {}
    for number, line in enumerate(lines[1:end], 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if not separator:
            raise BuildError(f"{rel}:{number}: ожидалось 'ключ: значение'")
        data[key.strip()] = _parse_scalar(value, f"{rel}:{number}")

    return data, "\n".join(lines[end + 1:]).strip("\n")


def build_bundle(
    slug: str,
    config: dict[str, object],
    manifest: dict[str, list[str]],
    check_only: bool,
) -> tuple[Path, Path | None, int]:
    """Собирает пакет навыка: SKILL.md-роутер + references/ + zip.

    Формат пакета совпадает с Claude Agent Skills и DSH: все файлы лежат в одном
    каталоге верхнего уровня, `SKILL.md` — в его корне.
    """
    rel = f"languages/{slug}/{ROUTER_NAME}"
    router = ROOT / rel
    if not router.is_file():
        raise BuildError(
            f"{rel}: нет роутера навыка. Нужен файл с заголовком name/description "
            "и ссылками references/*.md — он становится SKILL.md пакета."
        )

    front, body = _read_frontmatter(router, rel)
    name = str(config["name"])

    if front.get("name") != name:
        raise BuildError(
            f"{rel}: name '{front.get('name')}' не совпадает с name "
            f"'{name}' в languages/{slug}/config.yaml"
        )
    description = " ".join(str(front.get("description", "")).split())
    if not description:
        raise BuildError(f"{rel}: пустой description в заголовке")
    if len(description) > DESCRIPTION_MAX:
        raise BuildError(
            f"{rel}: description {len(description)} знаков, а каталог навыков "
            f"показывает только {DESCRIPTION_MAX} — сократите"
        )

    stages = stage_paths(slug, manifest)
    expected = {Path(path).name for path in stages}
    referenced = set(REFERENCE_RE.findall(body))

    unknown = sorted(referenced - expected)
    if unknown:
        raise BuildError(
            f"{rel}: ссылки на этапы, которых нет в сборке: {', '.join(unknown)}"
        )
    unused = sorted(expected - referenced)
    if unused:
        raise BuildError(
            f"{rel}: не упомянуты этапы: {', '.join(unused)}. "
            "Добавьте строки в маршрут или уберите этапы из scripts/stages.yaml."
        )

    bundle = SKILLS_DIR / name
    zip_path = SKILLS_DIR / f"{name}.zip"
    if check_only:
        return bundle, None, len(stages)

    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "references").mkdir(parents=True, exist_ok=True)

    (bundle / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {json.dumps(description, ensure_ascii=False)}\n---\n\n{body}\n",
        encoding="utf-8",
        newline="\n",
    )
    for path in stages:
        content = _substitute(_read_text(ROOT / path), config, path).strip("\n") + "\n"
        (bundle / "references" / Path(path).name).write_text(
            content, encoding="utf-8", newline="\n"
        )

    zip_bundle(name, bundle, zip_path)
    return bundle, zip_path, len(stages)


def zip_bundle(name: str, bundle: Path, target: Path) -> None:
    """Пакует пакет в <name>.zip: <name>/SKILL.md + <name>/references/*.md.

    Отметки времени фиксированы, чтобы одинаковый вход давал одинаковый zip.
    """
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        for path in sorted(bundle.rglob("*")):
            if not path.is_file():
                continue
            arcname = f"{name}/{path.relative_to(bundle).as_posix()}"
            info = ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())


def _bundle_summary(
    slug: str, bundle: Path, zip_path: Path | None, stages: int, check_only: bool
) -> str:
    prefix = "проверен " if check_only else "собран   "
    target = bundle.relative_to(ROOT).as_posix()
    if zip_path is None:
        size = ""
    else:
        size = f", {len(zip_path.read_bytes()) / 1024:.1f} KB zip"
    return (
        f"  {prefix} {slug:<8} {stages:>2} этапов "
        f"→ {target}/ ({bundle.name}/SKILL.md + references/){size}"
    )


def build_one(
    slug: str,
    config: dict[str, object],
    manifest: dict[str, list[str]],
    check_only: bool,
) -> tuple[Path, str, list[str]]:
    text, paths = build_text(slug, config, manifest)
    target = output_path(config)
    if not check_only:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
    return target, text, paths


def _summary_line(
    slug: str, target: Path, text: str, paths: list[str], check_only: bool
) -> str:
    common_count = sum(1 for p in paths if p.startswith("common/"))
    lang_count = len(paths) - common_count
    size_kb = len(text.encode("utf-8")) / 1024
    lines = text.count("\n")
    prefix = "проверено" if check_only else "собрано  "
    return (
        f"  {prefix} {slug:<8} {len(paths):>2} этапов "
        f"(common {common_count} + {slug} {lang_count}) "
        f"→ {target.relative_to(ROOT).as_posix()} "
        f"[{size_kb:.1f} KB, {lines} строк]"
    )


# --------------------------------------------------------------------------
# Режим --matrix (для GitHub Actions)
# --------------------------------------------------------------------------

def matrix_lines(
    configs: dict[str, dict[str, object]], manifest: dict[str, list[str]]
) -> list[str]:
    languages: list[dict[str, str]] = []
    publishable: list[dict[str, str]] = []

    for slug in sorted(configs):
        config = configs[slug]
        build_text(slug, config, manifest)  # валидируем конфиг до запуска джоб

        languages.append(
            {
                "slug": slug,
                "name": str(config["name"]),
                "path": f"output/{config['output_file']}",
                "file": str(config["output_file"]),
                "bundle": f"output/skills/{config['name']}.zip",
            }
        )
        publish_repo = str(config.get("publish_repo") or "").strip()
        if publish_repo:
            publishable.append(
                {
                    "slug": slug,
                    "name": str(config["name"]),
                    "file": str(config["output_file"]),
                    "publish_repo": publish_repo,
                }
            )

    def dump(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    return [
        f"languages={dump(languages)}",
        f"publishable={dump(publishable)}",
        f"has_publishable={'true' if publishable else 'false'}",
    ]


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="build.py",
        description="Собирает единые SKILL.md-артефакты из common/ и languages/<язык>/.",
    )
    parser.add_argument(
        "languages",
        nargs="*",
        metavar="ЯЗЫК",
        help="какие языки собирать (по умолчанию все найденные)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="только проверить конфиги и этапы, файлы не писать",
    )
    parser.add_argument(
        "--matrix",
        action="store_true",
        help="напечатать матрицу для GitHub Actions в формате key=value",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args(argv)

    try:
        manifest = load_manifest()
        configs = load_languages(manifest)

        if args.matrix:
            for line in matrix_lines(configs, manifest):
                print(line)
            return 0

        selected = args.languages or sorted(configs)
        unknown = [slug for slug in selected if slug not in configs]
        if unknown:
            available = ", ".join(sorted(configs))
            raise BuildError(
                f"неизвестный язык: {', '.join(unknown)}. Доступные: {available}"
            )

        print("Сборка SKILL-артефактов" + (" (проверка)" if args.check else ""))
        for slug in selected:
            target, text, paths = build_one(slug, configs[slug], manifest, args.check)
            print(_summary_line(slug, target, text, paths, args.check))
            bundle, zip_path, stages = build_bundle(
                slug, configs[slug], manifest, args.check
            )
            print(_bundle_summary(slug, bundle, zip_path, stages, args.check))
        return 0

    except BuildError as exc:
        print(f"ОШИБКА СБОРКИ: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
