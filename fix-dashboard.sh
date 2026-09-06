#!/bin/bash
# Script para corregir la animación 3D del dashboard

ssh root@178.104.253.211 << 'EOF'
# Variables
FILE="/var/www/dashboard/index.html"
BACKUP="/var/www/dashboard/index-backup.html"

# Verificar backup existe
if [ ! -f "$BACKUP" ]; then
    cp "$FILE" "$BACKUP"
    echo "Backup creado: $BACKUP"
fi

# 1. Corregir posición de nodos (más aleatoriedad)
# Buscar la línea con "const phi = Math.acos"
sed -i 's|const phi = Math.acos(1 - 2\*(i+0.5)/NODES.length);|const phi = Math.random() * Math.PI;|g' "$FILE"
sed -i 's|const theta = Math.PI \* (1 + Math.sqrt(5)) \* i \* 0.618;|const theta = Math.random() * Math.PI * 2;|g' "$FILE"
sed -i 's|const radius = 32 + Math.sin(i\*1.7)\*6;|const radius = 32 + Math.random() * 50;|g' "$FILE"

# 2. Mejorar diseño del núcleo (efecto video)
# Buscar la línea con "emissive:0x1a3a6b"
sed -i 's|emissive:0x1a3a6b|emissive:0x00ffff|g' "$FILE"
sed -i 's|emissiveIntensity: 0.6 + Math.sin(time \* 3) \* 0.4||g' "$FILE"  # Añadir al final del objeto

# 3. Añadir animación dinámica al núcleo
# Buscar la línea con "const coreIntensity = 1.0" y añadir código
sed -i 's|let coreIntensity = 1.0;|let coreIntensity = 1.0 + Math.sin(time \* 2) \* 0.3;|g' "$FILE"

# Verificar cambios
echo "Cambios aplicados. Verificando..."
grep -n "const phi\|const theta\|const radius\|emissive:\|coreIntensity" "$FILE" | head -10

echo "Hecho."
EOF
