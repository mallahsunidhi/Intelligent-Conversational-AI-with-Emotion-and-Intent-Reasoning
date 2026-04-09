# EmotiChat - Fixed Backend

This is a repaired version of the uploaded project.

## What was fixed
- Added a complete Flask app in `backend/main.py`
- Added database setup
- Added working routes for chat and analytics
- Added CSV export and heatmap generation
- Added fallback response logic when Ollama is not installed/running
- Added a basic HTML chat page
- Cleaned imports and app startup logic

## Run
```bash
cd backend
pip install -r requirements.txt
python main.py
```

Open: http://127.0.0.1:5000

## Optional Ollama
If you want real LLM responses:
1. Install Ollama
2. Run `ollama serve`
3. Pull a model: `ollama pull llama3.2`
4. Start the Flask app

If Ollama is not running, the app still works using fallback replies.
