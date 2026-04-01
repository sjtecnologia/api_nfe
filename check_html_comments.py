import os
import re

def check_html_files():
    """Verifica arquivos HTML em busca de comentários mal formatados"""
    
    print("🔍 Verificando arquivos HTML...\n")
    
    problematic_files = []
    
    for root, dirs, files in os.walk('templates'):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Verificar várias possibilidades de problema
                    issues = []
                    
                    # 1. Comentários HTML mal fechados
                    if '<!--' in content and '-->' not in content:
                        issues.append("Comentário HTML não fechado (<!--)")
                    
                    # 2. Comentários HTML órfãos
                    if '-->' in content and '<!--' not in content:
                        issues.append("Fechamento de comentário órfão (-->)")
                    
                    # 3. Verificar se começa com -->
                    if content.strip().startswith('-->'):
                        issues.append("Arquivo começa com fechamento de comentário (-->)")
                    
                    # 4. Verificar caracteres estranhos no início
                    first_line = content.split('\n')[0] if content else ""
                    if first_line and not first_line.strip().startswith(('<!DOCTYPE', '<html', '<%', '{%')):
                        if '-->' in first_line or '<!--' in first_line:
                            issues.append(f"Primeira linha suspeita: {first_line[:50]}...")
                    
                    # 5. Verificar encoding BOM
                    if content.startswith('\ufeff'):
                        issues.append("Arquivo contém BOM (Byte Order Mark)")
                    
                    if issues:
                        problematic_files.append((file_path, issues))
                        print(f"❌ {file_path}")
                        for issue in issues:
                            print(f"   • {issue}")
                        print()
                
                except Exception as e:
                    print(f"❌ Erro ao ler {file_path}: {e}")
    
    if not problematic_files:
        print("✅ Nenhum problema encontrado nos templates!")
    else:
        print(f"📊 Encontrados {len(problematic_files)} arquivos com problemas.")
    
    return problematic_files

def fix_html_files(problematic_files):
    """Tenta corrigir automaticamente os problemas"""
    
    if not problematic_files:
        print("Nenhum arquivo para corrigir.")
        return
    
    print("\n🔧 Tentando corrigir arquivos...\n")
    
    for file_path, issues in problematic_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Corrigir BOM
            if content.startswith('\ufeff'):
                content = content[1:]
                print(f"✅ {file_path}: Removido BOM")
            
            # Corrigir comentários órfãos no início
            if content.strip().startswith('-->'):
                lines = content.split('\n')
                # Remover a primeira linha se for apenas -->
                if lines[0].strip() == '-->':
                    content = '\n'.join(lines[1:])
                    print(f"✅ {file_path}: Removido '-->' do início")
            
            # Remover linhas que só contêm --> ou <!--
            lines = content.split('\n')
            cleaned_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped in ['-->', '<!--']:
                    print(f"✅ {file_path}: Removida linha: '{stripped}'")
                    continue
                cleaned_lines.append(line)
            
            content = '\n'.join(cleaned_lines)
            
            # Salvar se houve mudanças
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"💾 {file_path}: Arquivo corrigido e salvo")
            
        except Exception as e:
            print(f"❌ Erro ao corrigir {file_path}: {e}")

if __name__ == "__main__":
    problematic_files = check_html_files()
    
    if problematic_files:
        print("\n" + "="*50)
        fix_choice = input("Deseja tentar corrigir automaticamente? (s/n): ").lower()
        
        if fix_choice == 's':
            fix_html_files(problematic_files)
            print("\n🎉 Correção concluída! Teste a aplicação novamente.")
        else:
            print("Correção cancelada. Você pode corrigir manualmente os arquivos listados.")