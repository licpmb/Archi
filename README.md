# ArchiMate AI Generator

Generá modelos ArchiMate desde lenguaje natural usando IA.
Exportá directamente a Archi 4.x (`.archimate`) y Open Exchange Format (`.xml`).

## Características

- **Chat conversacional** – describí tu arquitectura en español o inglés
- **Todas las capas ArchiMate 3.x** – Motivación, Estrategia, Negocio, Aplicación, Tecnología, Física, Implementación
- **Exportación dual** – `.archimate` (Archi 4.x) + Open Exchange Format
- **Auto-layout** – el diagrama se genera automáticamente con elementos organizados por capa
- **Dos proveedores de IA**
  - **Ollama** – local, gratis, sin API key
  - **Anthropic Claude** – pago, mayor calidad

## Instalación

```bash
git clone <repo>
cd Archi
pip install -r requirements.txt
```

## Configuración de IA

### Opción 1: Ollama (gratis, local)

1. Instalá [Ollama](https://ollama.ai)
2. Descargá un modelo:
   ```bash
   ollama pull llama3.1
   ```
3. Iniciá el servidor:
   ```bash
   ollama serve
   ```
4. La app lo detecta automáticamente.

### Opción 2: Anthropic Claude (pago)

```bash
cp .env.example .env
# Editá .env y completá ANTHROPIC_API_KEY=sk-ant-...
```

## Uso

```bash
python app.py
# Abrí http://localhost:8000
```

Describí tu arquitectura en el chat:

> *"Tenemos un sistema CRM que usan los vendedores para gestionar clientes y pedidos. El CRM usa una base de datos Oracle y corre en AWS."*

La IA extrae los elementos ArchiMate, los muestra en el panel lateral y podés descargar el modelo en cualquier momento.

## Importar en Archi

1. Abrí Archi 4.x
2. **File → Open…** → seleccioná el archivo `.archimate` descargado

## Estructura del proyecto

```
app.py                    # FastAPI backend
archimate/
  model.py                # Clases del dominio + auto-layout
  xml_generator.py        # Generador .archimate (Archi 4.x)
  exchange_generator.py   # Open Exchange Format
ai/
  base.py                 # Sistema prompt + parsing JSON
  claude_provider.py      # Proveedor Claude
  ollama_provider.py      # Proveedor Ollama
templates/
  index.html              # UI de chat (single-page)
```
