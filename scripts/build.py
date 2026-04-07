#!/usr/bin/env python3
# scripts/build-skill.py

import os
import yaml
from pathlib import Path

def build_skill(language: str, config: dict):
    """Собирает SKILL.md из общих и языко-специфичных этапов"""
    
    output = []
    
    # 1. Заголовок скилла
    output.append(f"""---
name: {config['name']}
description: "{config['description']}"
---
""")
    
    # 2. Общие этапы (1-5)
    for stage in sorted(Path('common').glob('*.md')):
        content = Path(stage).read_text()
        output.append(f"\n\n<!-- {stage.name} -->\n{content}")
    
    # 3. Языко-специфичные этапы (6+)
    stages_dir = Path(f'languages/{language}/stages')
    for stage in sorted(stages_dir.glob('*.md')):
        content = Path(stage).read_text()
        # Заменяем плейсхолдеры на языко-специфичные
        content = replace_placeholders(content, config)
        output.append(f"\n\n<!-- {stage.name} -->\n{content}")
    
    # 4. Сохраняем результат
    output_file = Path(f'output/{config["output_file"]}')
    output_file.write_text('\n'.join(output))
    
    print(f"✅ Generated: {output_file}")

def replace_placeholders(content: str, config: dict) -> str:
    """Заменяет {{language}}, {{test_framework}} и т.д."""
    replacements = {
        '{{language}}': config['language'],
        '{{test_framework}}': config['test_framework'],
        '{{build_command}}': config['build_command'],
        '{{test_command}}': config['test_command'],
        '{{package_manager}}': config['package_manager'],
    }
    for k, v in replacements.items():
        content = content.replace(k, v)
    return content

if __name__ == '__main__':
    # Загружаем конфиги
    for lang_config in Path('languages').glob('*/config.yaml'):
        lang = lang_config.parent.name
        config = yaml.safe_load(lang_config.read_text())
        build_skill(lang, config)