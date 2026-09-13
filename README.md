# 📊 Chartify — Autonomous AI Data Visualization Studio

> Transform raw datasets into publication-ready, interactive visualizations through natural language prompts, powered by multi-provider LLM cascade and intelligent heuristic fail-safes.

---

## ⚡ Key Highlights

- 🗣️ **Natural Language to Visualizations**: Ask questions in plain English (e.g. *"Show correlation heatmap between sales and profit with dark magma theme"*) and receive statistical charts in milliseconds.
- 🚦 **4-Tier LLM Multi-Provider Cascade**:
  1. **Google Gemini** (`gemini-flash-latest`, `gemini-3.7-flash`)
  2. **Mistral AI** (`ministral-8b-latest`, `open-mistral-7b`)
  3. **Groq LPU** (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`)
  4. **Smart Heuristic Engine** (< 1ms zero-fail offline fallback)
- 📈 **Big Data Scalability Engine (1,000,000+ Rows)**: Dynamic intelligent data pre-processing:
  - Statistical aggregation for categorical charts (Bar, Donut, Treemap, Waterfall)
  - Smooth decimation for high-frequency time-series
  - Stratified sampling for scatter & distribution plots
- 🎨 **Chart Aesthetics Studio**:
  - Live base styles: *Whitegrid, Dark Glow, 538 Editorial, GGPlot, Dark Grid, Minimal*
  - Curated palettes: *Viridis, Plasma, Magma, Rocket, Crest, Coolwarm, Pastel, Colorblind-Safe*
  - Dual synchronized dropdowns & instant "Surprise Me" styling
- 🛡️ **Thread-Safe Concurrent Rendering**: Async FastAPI pipeline with background worker threads and thread-safe execution locks.
- 📱 **Modern Glassmorphic UI**: Built with React, Vite, Lucide Icons, and full Dark / Light mode responsiveness.

---

## 🏗️ Architecture

```
Chartify/
├── main.py              # AI Engine, Multi-LLM Cascade, Heuristics & Data Preprocessing
├── server.py            # FastAPI Async Server, CORS & Chart Rendering Endpoints
├── frontend/            # React + Vite Glassmorphic Dashboard
│   ├── src/
│   │   ├── App.jsx      # Interactive Studio, Dataset Inspector & Canvas
│   │   └── index.css    # Comprehensive Dark / Light Glassmorphism System
│   └── package.json
├── .env.example         # Template for environment variables
└── README.md
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- Node.js 18+

### 2. Backend Setup
```bash
# Clone the repository
git clone https://github.com/MeetR07/Chartify.git
cd Chartify

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install fastapi uvicorn pandas matplotlib seaborn langchain-google-genai langchain-mistralai langchain-groq python-dotenv

# Set up API keys
cp .env.example .env
# Edit .env with your Google Gemini, Mistral, or Groq keys
```

Run backend server:
```bash
python server.py
# Server starts on http://127.0.0.1:8000
```

### 3. Frontend Setup
```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server
npm run dev
# Frontend starts on http://localhost:5173
```

---

## 🔑 Environment Configuration

Create a `.env` file in the root directory:

```env
GOOGLE_API_KEY="your_gemini_api_key"
MISTRAL_API_KEY="your_mistral_api_key"
GROQ_API_KEY="your_groq_api_key"
```

---

## 📊 Supported Chart Types

- **Comparison**: Bar Charts, Stacked Bar, Grouped Bar
- **Trends & Time Series**: Line Charts, Area Plots
- **Distributions**: Histograms, KDE Density Plots, Boxplots, Violin Plots
- **Relationships**: Scatter Plots, Bubble Charts, Pair Plots
- **Composition & Parts-of-Whole**: Donut Charts, Treemaps, Pie Charts
- **Specialized**: Heatmaps, Correlation Matrices, Radar Spider, Waterfall, Lollipop

---

## 📜 License

MIT License. Crafted with ❤️ for data analysts, engineers, and scientists.
