# AGENTS.md - BatchGen Pro

> Guidelines for AI coding agents working on this repository

## Project Overview

BatchGen Pro is a full-stack AI batch image generation tool with a Vue.js frontend and Flask backend.

**Stack:**
- **Frontend:** Vue 3, Vite, Element Plus
- **Backend:** Flask, Celery, Redis
- **AI APIs:** Gemini, Doubao

## Build Commands

### Frontend (`/frontend`)
```bash
npm install     # Install dependencies
npm run dev     # Start dev server (port 8590)
npm run build   # Production build → dist/
npm run preview # Preview production build
```

### Backend (`/backend`)
```bash
# Setup
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run
python app.py              # Flask dev server (port 5001)
```

### Docker (Production)
```bash
docker-compose -f docker-compose.server.yml.example up -d --build
```

## Code Style Guidelines

### Vue.js (Frontend)

**Component Structure:**
```vue
<template>
  <!-- Template first -->
</template>

<script>
import { ref, watch } from 'vue'
// Imports: external first, then internal

export default {
  name: 'ComponentName',  // PascalCase
  props: {
    file: { type: File, default: null }
  },
  emits: ['event-name'],  // kebab-case for events
  setup(props, { emit }) {
    // Composition API only
    const localVar = ref('')
    
    const handler = () => {
      emit('event-name', value)
    }
    
    return { localVar, handler }
  }
}
</script>

<style scoped>
/* Scoped styles, BEM-like naming */
.component-name { }
.component-name__element { }
</style>
```

**Naming Conventions:**
- Components: PascalCase (`ImageUpload.vue`, `ApiConfigDialog.vue`)
- Props/Variables: camelCase (`fileSize`, `apiKey`)
- Events: kebab-case (`file-change`, `update:model`)
- CSS classes: kebab-case, scoped

**Imports:**
- External libraries first (Vue, Element Plus)
- Internal components/utils last
- Use named imports for Element Plus icons

### Python (Backend)

**Style:**
- Follow PEP 8
- 4-space indentation
- Maximum line length: 100 characters
- Docstrings: Triple double quotes, Chinese for project-specific docs

**File Organization:**
```python
#!/usr/bin/env python3
"""
模块描述
"""
# 1. Standard library imports
import os
import sys
import uuid

# 2. Third-party imports
from flask import Flask, request
from PIL import Image

# 3. Local imports
from task_manager import task_manager

# Environment setup
load_dotenv()

# Configuration constants (UPPER_SNAKE_CASE)
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 10 * 1024 * 1024))

# Flask app initialization
app = Flask(__name__)

# Routes and handlers
@app.route('/api/endpoint', methods=['POST'])
def handler():
    """Handler docstring"""
    pass
```

**Naming Conventions:**
- Modules: snake_case (`ai_image_generator.py`)
- Classes: PascalCase (`AIImageGenerator`, `TaskManager`)
- Functions/Variables: snake_case (`generate_image`, `api_key`)
- Constants: UPPER_SNAKE_CASE (`MAX_FILE_SIZE`, `GEMINI_MODEL`)

**Error Handling:**
```python
try:
    result = process_data()
except SpecificException as e:
    return jsonify({'error': str(e)}), 400
except Exception as e:
    # Log unexpected errors
    return jsonify({'error': 'Internal server error'}), 500
```

## Project Structure

```
BatchGenPro/
├── frontend/                 # Vue.js SPA
│   ├── src/
│   │   ├── components/       # Vue components (.vue files)
│   │   ├── utils/           # Utility functions
│   │   ├── App.vue          # Root component
│   │   └── main.js          # Entry point
│   ├── public/              # Static assets
│   ├── dist/                # Build output
│   ├── vite.config.js       # Vite configuration
│   └── package.json
├── backend/                 # Flask API
│   ├── app.py               # Main Flask application
│   ├── ai_image_generator.py # AI client abstraction
│   ├── task_manager.py      # Task queue management
│   ├── tasks.py             # Celery tasks
│   ├── celery_config.py     # Celery configuration
│   ├── daily_limit_manager.py # Rate limiting
│   ├── uploads/             # Uploaded images
│   ├── results/             # Generated images
│   └── requirements.txt
├── docker/                  # Docker configurations
├── docker-compose.server.yml.example  # Docker Compose template
├── env.example              # Environment variables template
└── .env                     # Local environment (not in git)
```

## API Patterns

**Frontend → Backend:**
- Base URL: `http://localhost:5001`
- Vite proxy: `/api` → `http://localhost:5001`
- Content-Type: `multipart/form-data` for image uploads
- JSON for other requests

**Backend Response Format:**
```python
# Success
return jsonify({
    'success': True,
    'data': { ... },
    'message': '可选的成功消息'
}), 200

# Error
return jsonify({
    'success': False,
    'error': '错误描述'
}), 400
```

## Environment Variables

Key variables from `env.example`:
- `REDIS_PASSWORD` - Redis authentication
- `GEMINI_MODEL`, `DOUBAO_MODEL` - Default AI models
- `MAX_FILE_SIZE` - Upload limit (default: 10MB)
- `UPLOAD_FOLDER`, `RESULT_FOLDER` - File paths

## Development Notes

**No Testing Framework:** This project currently has no configured test framework. Add tests using pytest (backend) or Vitest (frontend) if needed.

**No Linting:** No ESLint or Prettier configured. Follow style guidelines manually.

**No TypeScript:** JavaScript only. Use JSDoc for complex function documentation.

**Security:**
- API keys stored in browser localStorage only
- No server-side API key storage
- File uploads validated for type and size
- CORS enabled for development

## Common Tasks

**Add a new AI provider:**
1. Update `SUPPORTED_APIS` in `.env`
2. Add initialization in `ai_image_generator.py`
3. Add UI option in `ApiConfigDialog.vue`

**Add a new API endpoint:**
1. Add route in `backend/app.py`
2. Add service function if needed
3. Add API call in frontend utils
4. Update component to use new endpoint

**Add a Vue component:**
1. Create `.vue` file in `frontend/src/components/`
2. Use Composition API (`setup` function)
3. Add scoped styles
4. Import and use in parent component
