#!/bin/bash
# ==============================================================================
# Script de Construção do Pacote .DEB do ZeroFreeze
# Gera um instalador profissional com duplo clique para Zorin OS, Mint e Ubuntu
# ==============================================================================
set -e

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BUILD_DIR="/tmp/zerofreeze_deb_build"
VERSION="1.0.0"
PACKAGE_NAME="zerofreeze"
DEB_FILENAME="${PACKAGE_NAME}_${VERSION}_all.deb"
DIST_DIR="${PROJECT_DIR}/dist"

echo "=================================================="
echo "📦 Construindo pacote .DEB: ${DEB_FILENAME}"
echo "=================================================="

# 1. Limpa diretórios temporários anteriores
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/opt/zerofreeze"
mkdir -p "${BUILD_DIR}/usr/bin"
mkdir -p "${BUILD_DIR}/usr/share/applications"
mkdir -p "${DIST_DIR}"

# 2. Copia arquivos da aplicação para /opt/zerofreeze
echo "-> Copiando código-fonte e recursos para /opt/zerofreeze..."
cp -r "${PROJECT_DIR}/src" "${BUILD_DIR}/opt/zerofreeze/"
cp -r "${PROJECT_DIR}/assets" "${BUILD_DIR}/opt/zerofreeze/"
cp "${PROJECT_DIR}/config.json" "${BUILD_DIR}/opt/zerofreeze/"
cp "${PROJECT_DIR}/run.sh" "${BUILD_DIR}/opt/zerofreeze/"

# Remove quaisquer caches .pyc ou __pycache__ do pacote
find "${BUILD_DIR}/opt/zerofreeze" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${BUILD_DIR}/opt/zerofreeze" -name "*.pyc" -delete 2>/dev/null || true

chmod +x "${BUILD_DIR}/opt/zerofreeze/run.sh"

# 3. Cria o executável no PATH (/usr/bin/zerofreeze)
cat << 'EOF' > "${BUILD_DIR}/usr/bin/zerofreeze"
#!/bin/bash
exec /opt/zerofreeze/run.sh "$@"
EOF
chmod 755 "${BUILD_DIR}/usr/bin/zerofreeze"

# 4. Copia os ícones oficiais para o tema de ícones do sistema
for size in 16 32 48 64 128 256 512; do
    ICON_SRC="${PROJECT_DIR}/assets/icons/zerofreeze-${size}.png"
    if [ "$size" -eq 512 ] && [ ! -f "$ICON_SRC" ]; then
        ICON_SRC="${PROJECT_DIR}/assets/icons/zerofreeze.png"
    fi
    if [ -f "$ICON_SRC" ]; then
        DEST_DIR="${BUILD_DIR}/usr/share/icons/hicolor/${size}x${size}/apps"
        mkdir -p "$DEST_DIR"
        cp "$ICON_SRC" "${DEST_DIR}/zerofreeze.png"
    fi
done

# 5. Cria o atalho no menu do sistema (/usr/share/applications/zerofreeze.desktop)
cat << EOF > "${BUILD_DIR}/usr/share/applications/zerofreeze.desktop"
[Desktop Entry]
Name=ZeroFreeze
Comment=Monitor de Sistema & Salvaguarda Anti-Travamento para Linux
Exec=/usr/bin/zerofreeze
Icon=zerofreeze
Terminal=false
Type=Application
Categories=Utility;System;Monitor;
StartupNotify=false
EOF
chmod 644 "${BUILD_DIR}/usr/share/applications/zerofreeze.desktop"

# 6. Cria o arquivo de controle DEBIAN/control
cat << EOF > "${BUILD_DIR}/DEBIAN/control"
Package: ${PACKAGE_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: all
Maintainer: Linker <linker@zerofreeze.app>
Depends: python3, python3-gi, python3-gi-cairo, gir1.2-gtk-3.0, python3-psutil, python3-pil
Description: Monitor de Sistema & Salvaguarda Anti-Travamento para Linux
 ZeroFreeze e um gerenciador inteligente de memoria RAM, CPU e armazenamento
 com widget contabil retratil flutuante e salvaguarda ativa contra congelamento do sistema.
 Projetado para Zorin OS, Linux Mint, Ubuntu e derivados.
EOF

# 7. Script de pós-instalação (atualiza caches de ícones e menu)
cat << 'EOF' > "${BUILD_DIR}/DEBIAN/postinst"
#!/bin/sh
set -e
if which update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if which gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
exit 0
EOF
chmod 755 "${BUILD_DIR}/DEBIAN/postinst"

# 8. Script de pós-remoção
cat << 'EOF' > "${BUILD_DIR}/DEBIAN/postrm"
#!/bin/sh
set -e
if which update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if which gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
exit 0
EOF
chmod 755 "${BUILD_DIR}/DEBIAN/postrm"

# 9. Empacota com dpkg-deb
dpkg-deb --build --root-owner-group "${BUILD_DIR}" "${DIST_DIR}/${DEB_FILENAME}"

# 10. Copia para a Área de Trabalho para facilitar o envio pelo Linker
cp "${DIST_DIR}/${DEB_FILENAME}" "/home/linker/Área de trabalho/${DEB_FILENAME}"

# 11. Limpeza
rm -rf "${BUILD_DIR}"

echo "=================================================="
echo "✅ Pacote gerado com sucesso!"
echo "📍 Arquivo disponível em:"
echo "   1) ${DIST_DIR}/${DEB_FILENAME}"
echo "   2) /home/linker/Área de trabalho/${DEB_FILENAME}"
echo "=================================================="
