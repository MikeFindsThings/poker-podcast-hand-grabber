# 🃏 Poker Hand Analyzer

Automatically extract and analyze poker hands from podcast episodes using AI transcription and pattern recognition.

## Features

- 🎧 **RSS Feed Processing**: Automatically download latest podcast episodes
- 🎤 **AI Transcription**: Use OpenAI Whisper for accurate speech-to-text
- 🔍 **Hand Detection**: Identify poker hand discussions with confidence scoring  
- 📊 **Detailed Reports**: Generate timestamped markdown reports
- 🤖 **GitHub Actions**: Automated processing when new episodes are released
- 🍎 **Apple Silicon Optimized**: Fast processing on M1/M2/M3 Macs

## Quick Start

### Local Usage

```bash
# Clone and setup
git clone <repo-url>
cd poker-hand-analyzer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install system dependencies (macOS)
brew install ffmpeg

# Process latest episode
python3 src/cli.py --rss "https://feeds.buzzsprout.com/2227971.rss"

# Process multiple episodes
python3 src/cli.py --rss "https://feeds.buzzsprout.com/2227971.rss" --max-episodes 3

# Use different Whisper model
python3 src/cli.py --rss "https://feeds.buzzsprout.com/2227971.rss" --model turbo
```

### Automated Processing

Enable GitHub Actions to automatically process new episodes:

1. Fork this repository
2. Enable GitHub Actions in repository settings
3. The workflow runs daily at 9 AM UTC
4. Manual runs available via "Actions" tab

## Configuration

### Supported Podcasts

Currently optimized for:
- **Suited Kings Poker** - `https://feeds.buzzsprout.com/2227971.rss`

### Whisper Models

| Model | Speed | Accuracy | RAM Usage |
|-------|-------|----------|-----------|
| `tiny` | Fastest | Good | ~1GB |
| `base` | Fast | Better | ~1GB |
| `small` | Moderate | Good | ~2GB |
| `medium` | Slower | Very Good | ~5GB |
| `large` | Slowest | Best | ~10GB |
| `turbo` | Fast | Very Good | ~6GB |

## Output

For each processed episode, you get:
- `episode_audio.mp3` - Downloaded audio file
- `episode_transcript.json` - Full transcript with timestamps
- `episode_poker_hands.md` - Detected hands with timestamps
- `episode_data.json` - Processing metadata

## Hand Detection

The analyzer looks for:
- ✅ Specific card mentions (pocket aces, suited connectors)
- ✅ Betting actions (raises, calls, folds)
- ✅ Hand structure (preflop, flop, turn, river)
- ✅ Context clues (hand analysis, breakdowns)

## Requirements

- Python 3.11+
- FFmpeg
- 8GB+ RAM (for medium+ Whisper models)
- ~100MB storage per episode

## Development

```bash
# Run tests
pytest tests/

# Format code
black src/

# Type checking
mypy src/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add your improvements
4. Submit a pull request

## License

MIT License - see LICENSE file for details.