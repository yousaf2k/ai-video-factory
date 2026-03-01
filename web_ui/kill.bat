npx kill-port 8000
npx kill-port 3000
python -B -c "import uvicorn; uvicorn.run('web_ui.backend.main:app', host='127.0.0.1', port=8000, reload=False)"