"""Gera GameRegistration.zip pronto para enviar aos amigos."""
import zipfile
import os

FILES = [
    "app.py",
    "launcher.py",
    "requirements.txt",
    "INICIAR.bat",
    "README.md",
]

OUTPUT = "GameRegistration.zip"

print("Gerando pacote...")
with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for f in FILES:
        if os.path.exists(f):
            zf.write(f, f"GameRegistration/{f}")
            print(f"  + {f}")
        else:
            print(f"  ! Nao encontrado: {f}")

size_kb = os.path.getsize(OUTPUT) / 1024
print(f"\nPacote criado: {OUTPUT}  ({size_kb:.1f} KB)")
print("\nInstrucoes para os amigos:")
print("  1. Descompactar GameRegistration.zip")
print("  2. Executar setup.bat  (uma vez, instala dependencias)")
print("  3. Executar run.bat    (abre o app)")
