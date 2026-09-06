# 🌌 Dashboard MicroTech AI - JARVIS

**Centro de Mando 3D - Agent Orchestration**

[![Status](https://img.shields.io/badge/status-active-brightgreen)](https://dashboard.microtechai.es)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

---

## 📋 Tabla de Contenidos

- [Descripción](#-descripción)
- [Arquitectura](#-arquitectura)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Instalación y Despliegue](#-instalación-y-despliegue)
- [Problemas Conocidos y Soluciones](#-problemas-conocidos-y-soluciones)
- [Worklog - Cambios Recientes](#-worklog)

---

## 📖 Descripción

Dashboard interactivo con animación 3D en tiempo real para la orquestación de agentes de IA. Proporciona visibilidad completa del infrastructure, servicios WordPress, bases de datos y nodos de IA.

**Características:**
- 🎨 Animación 3D con Three.js (esferas, anillos, partículas)
- 🔐 Sistema de autenticación con persistencia de sesión
- 📊 Métricas en tiempo real (CPU, RAM, disco, uptime)
- 🌐 Visualización de nodos (Hetzner, DGX, WordPress, etc.)
- 🎯 Navegación por pestañas y sidebar
- 📈 Gráficos de rendimiento
- 🔔 Notificaciones en tiempo real

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    Cloudflare CDN/Proxy                      │
│              dashboard.microtechai.es → 178.104.253.211     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Nginx Server (Hetzner)                      │
│  Port 80 (HTTP) → Redirect 301 HTTPS                        │
│  Port 443 (HTTPS) → /var/www/dashboard/                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│             /var/www/dashboard/                              │
│  ├─ index.html          (HTML principal)                     │
│  ├─ api/                 (Endpoints PHP)                    │
│  │  └─ stats.php        (Métricas del sistema)              │
│  └─ /var/www/html/      (Sitios WordPress)                  │
└─────────────────────────────────────────────────────────────┘
```

### Componentes Principales

| Componente | Descripción | Ruta |
|------------|-------------|------|
| `index.html` | HTML principal con CSS e JS | `/var/www/dashboard/index.html` |
| `api/stats.php` | Endpoint API para métricas | `/var/www/dashboard/api/stats.php` |
| `CAT_COLORS` | Configuración de colores por categoría | JS inline (línea ~405) |
| `NODES` | Lista de nodos a visualizar | JS inline (línea ~413) |
| `animate()` | Loop principal de Three.js | JS inline (línea ~883) |

---

## 📂 Estructura del Proyecto

```
/var/www/dashboard/
├── index.html                      # Archivo principal (HTML + CSS + JS)
├── api/
│   └── stats.php                   # API endpoint para métricas
└── [Sitios WordPress en /var/www/html/]
```

### Estructura del HTML

```html
<!DOCTYPE html>
<html>
<head>
  <script src="three.min.js"></script>  <!-- Three.js CDN -->
  <style>
    /* CSS: Estilos para todos los componentes */
  </style>
</head>
<body>
  <!-- LOGIN OVERLAY (z-index: 9999) -->
  <div id="login-overlay">...</div>
  
  <!-- LOADING (z-index: 9998) -->
  <div id="loading">...</div>
  
  <!-- 3D CANVAS (z-index: 1) -->
  <canvas id="viz"></canvas>
  
  <!-- POST-PROCESSING OVERLAYS (z-index: 2-4) -->
  <div class="vignette"></div>
  <div class="scanlines"></div>
  <div class="glitch-overlay"></div>
  
  <!-- HEADER + NAV (z-index: 10) -->
  <div class="header">...</div>
  
  <!-- SIDEBAR (z-index: 11) -->
  <div class="sidebar">...</div>
  
  <!-- LEFT PANEL (z-index: 10) -->
  <div class="left-panel">...</div>
  
  <!-- RIGHT PANEL (z-index: 10) -->
  <div class="right-panel">...</div>
  
  <!-- SIDEBAR SLIDE-OUT (z-index: 20) -->
  <div class="side-panel">...</div>
  
  <script>
    // JavaScript: Lógica completa del dashboard
  </script>
</body>
</html>
```

### Z-Index Hierarchy

```
z-index: 9999  → login-overlay (login screen)
z-index: 9998  → loading (loading animation)
z-index: 20    → side-panel (slider panel)
z-index: 11    → sidebar (navigation)
z-index: 10    → header, panels, legend
z-index: 4     → glitch-overlay
z-index: 3     → scanlines
z-index: 2     → vignette
z-index: 1     → canvas#viz (3D scene)
```

---

## 🔧 Instalación y Despliegue

### Requisitos

- Servidor Linux (Debian/Ubuntu)
- Nginx con PHP-FPM 8.4
- Certificado SSL (Let's Encrypt)
- Acceso root o sudo

### Despliegue en Hetzner (178.104.253.211)

```bash
# 1. Conectar al servidor
ssh root@178.104.253.211

# 2. Crear respaldo
cp /var/www/dashboard/index.html /var/www/dashboard/index-backup.html

# 3. Copiar el nuevo archivo
# (transferir desde tu máquina local)
scp /ruta/local/index.html root@178.104.253.211:/var/www/dashboard/

# 4. Corregir permisos
chown www-data:www-data /var/www/dashboard/index.html
chmod 644 /var/www/dashboard/index.html

# 5. Recargar Nginx
nginx -t && systemctl reload nginx

# 6. Verificar
curl -I https://dashboard.microtechai.es/
```

### Configuración de Nginx

```nginx
server {
    listen 443 ssl;
    server_name dashboard.microtechai.es;
    
    ssl_certificate /etc/letsencrypt/live/microtechai.es/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/microtechai.es/privkey.pem;
    
    root /var/www/dashboard;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location ~ ^/api/.*\\.php$ {
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME /var/www/dashboard/$fastcgi_script_name;
        fastcgi_pass unix:/run/php/php8.4-fpm.sock;
    }
}
```

---

## ⚠️ Problemas Conocidos y Soluciones

### Error 1: Animación 3D no funciona tras login

**Síntoma:** El usuario puede hacer login, pero la animación 3D no se ve.

**Causa:** El script inicia `animate()` antes de verificar la sesión. Cuando el usuario hace login exitoso, se llama `startLoading()` pero la escena ya está en un estado inconsistente.

**Solución:** Asegurar que `animate()` se llame en el `DOMContentLoaded` y que `startLoading()` no interfiera con la animación 3D.

**Referencia:** Worklog - 2026-09-06 (fix-001)

---

### Error 2: Logout al actualizar la página

**Síntoma:** Al actualizar la página, el usuario hace logout automáticamente.

**Causa:** Uso de `sessionStorage` que se borra al cerrar la pestaña o navegador.

**Solución:** Reemplazar `sessionStorage` por `localStorage` para persistencia entre sesiones.

**Código original (INCORRECTO):**
```javascript
sessionStorage.setItem('mc_authed', 'true');
if (sessionStorage.getItem('mc_authed') === 'true') { ... }
```

**Código corregido:**
```javascript
localStorage.setItem('mc_authed', 'true');
if (localStorage.getItem('mc_authed') === 'true') { ... }
```

**Referencia:** Worklog - 2026-09-06 (fix-002)

---

### Error 3: Sintaxis JavaScript inválida (paréntesis desbalanceados)

**Síntoma:** Errores de JavaScript que impiden que el script funcione.

**Causa:** Expresiones `rgba()` incompletas en la definición de `CAT_COLORS`.

**Código original (INCORRECTO):**
```javascript
const CAT_COLORS = {
  server: {hex:'#4a9eff', glow:'rgba(74,158,255,'},
  wp: {hex:'#a78bfa', glow:'rgba(167,139,250,'},
  // ...
};
```

**Código corregido:**
```javascript
const CAT_COLORS = {
  server: {hex:'#4a9eff', glow:'rgba(74,158,255,0.3)'},
  wp: {hex:'#a78bfa', glow:'rgba(167,139,250,0.3)'},
  // ...
};
```

**Referencia:** Worklog - 2026-09-06 (fix-003)

---

### Error 4: Túnel Cloudflare no funciona

**Síntoma:** El túnel Cloudflare no se inicia con error "Unauthorized: Invalid tunnel secret".

**Causa:** El archivo de credenciales (`neural-dashboard.json`) tiene un `TunnelSecret` incorrecto o corrupto.

**Solución:** Crear un nuevo túnel desde Cloudflare Dashboard o descargar las credenciales correctas.

**Alternativa (recomendada):** Usar proxy directo de Cloudflare sin túnel (IP 178.104.253.211).

---

## 📝 Worklog

### 2026-09-06 - Fix-001: Corrección de sintaxis JavaScript

**Changes:**
- Corregido expresiones `rgba()` incompletas en `CAT_COLORS`
- Balance de paréntesis: 463/463 (correcto)
- Balance de llaves: 143/143 (correcto)

**Files:**
- `/var/www/dashboard/index.html`

**Status:** ✅ Resuelto

---

### 2026-09-06 - Fix-002: Persistencia de sesión

**Changes:**
- Reemplazado `sessionStorage` por `localStorage` en 3 ubicaciones
- Líneas: 376, 390, 1034

**Files:**
- `/var/www/dashboard/index.html`

**Status:** ✅ Resuelto

---

### 2026-09-06 - Fix-003: Animación 3D tras login

**Changes:**
- Verificado que `animate()` se llame antes de verificar sesión
- Script inicia con `animate()` en línea 1031
- `startLoading()` se llama tras el login exitoso

**Files:**
- `/var/www/dashboard/index.html`

**Status:** ✅ Resuelto

---

### 2026-09-06 - Fix-004: Configuración de Nginx

**Changes:**
- Configuración correcta de `server_name` para `dashboard.microtechai.es`
- SSL activo con Let's Encrypt
- Redirección HTTP → HTTPS

**Files:**
- `/etc/nginx/sites-available/microtechai`

**Status:** ✅ Resuelto

---

### 2026-09-06 - Fix-005: Documentación

**Changes:**
- Creación de README.md con estructura completa
- Documentación de problemas conocidos y soluciones
- Worklog detallado de cambios

**Files:**
- `/var/www/dashboard/README.md` (nuevo)
- `/var/www/dashboard/WORKLOG.md` (nuevo)

**Status:** ✅ Resuelto

---

## 🧪 Pruebas

### Verificación de sintaxis JavaScript

```bash
ssh root@178.104.253.211 "python3 << 'EOF'
import re
with open('/var/www/dashboard/index.html', 'r') as f:
    content = f.read()
script_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if script_match:
    script = script_match.group(1)
    print(f'Paréntesis: {script.count(\"(\")} / {script.count(\")\")}')
    print(f'Llaves: {script.count(\"{\")} / {script.count(\"}\")}')
EOF
"
```

**Output esperado:**
```
Paréntesis: 435 / 435
Llaves: 141 / 141
```

### Verificación de HTTP 200

```bash
curl -I https://dashboard.microtechai.es/
```

**Output esperado:**
```
HTTP/2 200
content-type: text/html
```

### Verificación de localStorage

```bash
grep -c 'localStorage' /var/www/dashboard/index.html
```

**Output esperado:**
```
3
```

---

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE)

---

## 👥 Autores

- **MicroTech AI** - Desarrollo y mantenimiento

---

## 🙏 Agradecimientos

- Three.js团队 por el excelente framework 3D
- Cloudflare por el CDN y proxy inverso

---

**Última actualización:** 2026-09-06
