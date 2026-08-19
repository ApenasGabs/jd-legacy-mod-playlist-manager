#!/bin/bash
# Script para compilar o JD2022LMPlaylistManager como AppImage localmente

set -e

echo "=> Instalando dependências python..."
pip install -r app/requirements.txt
pip install pyside6 zstandard cx_Freeze Pillow

echo "=> Entrando no diretório app..."
cd app

echo "=> Convertendo o ícone (.ico para .png)..."
python -c "from PIL import Image; Image.open('resources/gui/icon.ico').save('resources/gui/icon.png')"

echo "=> Construindo o executável com cx_Freeze..."
# Remove output antigo se existir
rm -rf build_output
python setup.py build

echo "=> Preparando o AppDir..."
rm -rf AppDir
mkdir -p AppDir/usr/bin
cp -r build_output/* AppDir/usr/bin/

mkdir -p AppDir/usr/bin/runtime
# Copia o songs.json se ele não tiver sido copiado pelo cx_Freeze
if [ -f runtime/songs.json ]; then
    cp runtime/songs.json AppDir/usr/bin/runtime/
fi

echo "=> Empacotando libxcb-cursor (compatibilidade com mais distros)..."
mkdir -p AppDir/usr/lib
XCURSOR_SO=$(find /usr -name 'libxcb-cursor.so.0*' -print -quit 2>/dev/null)
if [ -n "$XCURSOR_SO" ]; then
    cp -L "$XCURSOR_SO" AppDir/usr/lib/libxcb-cursor.so.0
    echo "   Encontrado: $XCURSOR_SO"
else
    echo "   AVISO: libxcb-cursor.so.0 não encontrado. Instale com: sudo apt install libxcb-cursor0"
fi

echo "=> Criando arquivo .desktop..."
cat <<EOF > AppDir/JD2022LMPlaylistManager.desktop
[Desktop Entry]
Name=JD2022LMPlaylistManager
Exec=JD2022LMPlaylistManager
Icon=icon
Type=Application
Categories=Utility;
EOF

echo "=> Copiando ícone e configurando o AppRun..."
cp resources/gui/icon.png AppDir/icon.png
cat <<'APPRUN' > AppDir/AppRun
#!/bin/bash
export LD_LIBRARY_PATH="$APPDIR/usr/lib:${LD_LIBRARY_PATH}"
exec "$APPDIR/usr/bin/JD2022LMPlaylistManager" "$@"
APPRUN
chmod +x AppDir/AppRun

echo "=> Baixando o appimagetool (caso não exista)..."
if [ ! -f "appimagetool" ]; then
    wget -O appimagetool "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x appimagetool
fi

echo "=> Gerando o AppImage final..."
# A flag --appimage-extract-and-run ajuda a rodar o gerador mesmo em containers/ambientes sem FUSE
ARCH=x86_64 ./appimagetool --appimage-extract-and-run AppDir ../JD2022LMPlaylistManager-x86_64.AppImage

echo "=> Sucesso! O arquivo JD2022LMPlaylistManager-x86_64.AppImage foi gerado na raiz do projeto."
