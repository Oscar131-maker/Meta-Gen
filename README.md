# MetaGen

Aplicación web para generar Meta Tags (Titles y Descriptions) optimizados para SEO utilizando IA (OpenAI y Anthropic) y datos de la SERP (SerperDev).

## Estructura del Proyecto

- `dev/backend`: Código del servidor FastAPI y utilidades (Scraper, LLM, Serper).
- `dev/frontend`: Código de la interfaz de usuario (HTML, CSS, JS).

## Requisitos Previos

- Python 3.8+
- Claves de API:
    - OpenAI
    - Anthropic
    - Serper Dev (incluida por defecto una clave de prueba en el código)

## Instalación y Ejecución Local

1. **Crear entorno virtual**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```

2. **Instalar dependencias**:
   ```powershell
   pip install -r dev/backend/requirements.txt
   playwright install chromium
   ```

3. **Configurar Variables de Entorno**:
   - Renombra `dev/backend/.env` (si existe o crea uno) y agrega tus claves:
     ```env
     OPENAI_API_KEY=tu_clave_aqui
     ANTHROPIC_API_KEY=tu_clave_aqui
     SERPER_API_KEY=tu_clave_aqui
     ```

4. **Ejecutar el Servidor**:
   Desde la raíz del proyecto (`c:\Storage\DEV\MetaGen`):
   ```powershell
   uvicorn dev.backend.main:app --reload
   ```

5. **Acceder a la App**:
   Abre [http://localhost:8000](http://localhost:8000) en tu navegador.

## Despliegue en Railway

1. Sube este repositorio a GitHub.
2. Crea un nuevo proyecto en Railway desde el repo.
3. Configura las variables de entorno (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.) en Railway.
4. Railway detectará `requirements.txt`.
5. **Configurar el comando de inicio (Start Command)** en Railway:
   ```bash
   uvicorn dev.backend.main:app --host 0.0.0.0 --port $PORT
   ```
   *Nota: Railway instala automáticamente las dependencias de requirements.txt. Si necesitas playwright, asegúrate de que el build process lo instale. Puedes usar un `nixpacks.toml` o agregar `playwright install chromium` al comando de build si es posible, o usar el start command como:*
   ```bash
   playwright install chromium && uvicorn dev.backend.main:app --host 0.0.0.0 --port $PORT
   ```

## Notas
- Los logs del proceso se muestran en tiempo real en la interfaz.
- El historial se guarda en el almacenamiento local del navegador.
