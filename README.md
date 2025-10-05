# smart-shelf-llm

LLM-powered grocery inventory management system using OCR and intelligent usage scheduling.

## Features

- **OCR-Based Product Logging**: Upload photos of product labels to automatically extract name, category, quantity, and expiry date
- **Intelligent Usage Scheduling**: AI-generated meal plans using Mixture of Experts approach (Nutrition, Budget, Recipe perspectives)
- **Smart Removal Prompts**: Automated suggestions to remove expired items
- **Fresh Produce Support**: Manual entry with AI-estimated shelf life
- **Persistent Storage**: Inventory data saved between sessions

## Prerequisites

- Python 3.8+
- Tesseract OCR
- Ollama with Llama3 model

## Installation & Usage

### 1. Install Tesseract OCR

**Windows:**
- Download from: https://github.com/UB-Mannheim/tesseract/wiki
- Add to PATH or set path in code

**Mac:**
```bash
brew install tesseract
```
**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

### 2. Install Ollama and Llama3

Download Ollama from https://ollama.com/

```bash
# Pull Llama3 model
ollama pull llama3
```

### 3. Clone Repository
```bash
git clone https://github.com/GrimGamer1999/smart-shelf-llm.git
cd smart-shelf-llm
```

### 4. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the App
```bash
streamlit run app.py
```
