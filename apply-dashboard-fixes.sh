#!/bin/bash
# Script para aplicar correcciones al dashboard con patching directo

ssh root@178.104.253.211 << 'EOF'
cd /var/www/dashboard

# Backup
cp index.html index-backup-codex2.html
echo "Backup creado: index-backup-codex2.html"

# 1. Corregir línea de núcleo (línea 570)
sed -i '570s/emissive:0x00ffff,shininess:100,transparent:true,opacity:0.8);/emissive:0x00ffff,emissiveIntensity:0.8,shininess:150,transparent:true,opacity:0.8);/' index.html

# 2. Añadir coreIntensity dinámico (línea 492)
sed -i '492s/let coreIntensity = 1.0;/let coreIntensity = 1.0 + Math.sin(time * 2) * 0.3;/' index.html

# 3. Añadir animación dinámica del núcleo (línea 903 - después de coreLight.intensity)
sed -i '903a\  // Breathing del núcleo\n  const pulse = 1 + Math.sin(time * 2) * 0.15;\n  coreMesh.scale.set(pulse, pulse, pulse);' index.html

# 4. Añadir rotación de anillos más dinámica (línea 913)
sed -i '913s/ring.rotation.z = time \* ring.userData.rotSpeed \* 10;/ring.rotation.z = time * ring.userData.rotSpeed * 15;/' index.html

echo "Correcciones aplicadas."

# Verificar
python3 << 'PYTHON'
import re
with open('/var/www/dashboard/index.html', 'r') as f:
    c = f.read()
m = re.search(r'<script>(.*?)</script>', c, re.DOTALL)
s = m.group(1) if m else ''
print(f'Paréntesis: {s.count("(")} / {s.count(")")}')
print(f'Llaves: {s.count("{")} / {s.count("}")}')
if s.count('(') == s.count(')') and s.count('{') == s.count('}'):
    print('✅ Sintaxis OK')
else:
    print('❌ Sintaxis ERROR')
PYTHON

echo "Hecho."
EOF
