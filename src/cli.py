#!/usr/bin/env python3
"""
Poker Hand Analyzer CLI
Extract and visualize poker hands from podcast RSS feeds
"""

import argparse
import sys
from pathlib import Path
import whisper
import json
from datetime import datetime
import feedparser
import requests
from urllib.parse import urlparse
import tempfile
import os
import ssl

# Fix SSL certificate issues on macOS
ssl._create_default_https_context = ssl._create_unverified_context

class PokerHandAnalyzer:
    def __init__(self, model_size="medium"):
        """Initialize with Whisper model"""
        print(f"Loading Whisper model: {model_size}...")
        self.whisper_model = whisper.load_model(model_size)
        print("✓ Model loaded successfully")
    
    def fetch_rss_episodes(self, rss_url, max_episodes=5, skip_episodes=0):
        """Fetch latest episodes from RSS feed"""
        print(f"Fetching RSS feed: {rss_url}")
        
        try:
            feed = feedparser.parse(rss_url)
            if feed.bozo:
                raise ValueError(f"Invalid RSS feed: {feed.bozo_exception}")
            
            episodes = []
            # Skip episodes and then take max_episodes
            for entry in feed.entries[skip_episodes:skip_episodes + max_episodes]:
                # Find audio enclosure
                audio_url = None
                for enclosure in getattr(entry, 'enclosures', []):
                    if enclosure.type.startswith('audio/'):
                        audio_url = enclosure.href
                        break
                
                if audio_url:
                    episodes.append({
                        'title': entry.title,
                        'published': getattr(entry, 'published', 'Unknown'),
                        'audio_url': audio_url,
                        'description': getattr(entry, 'summary', ''),
                        'guid': getattr(entry, 'id', entry.title)
                    })
            
            print(f"✓ Found {len(episodes)} episodes with audio")
            return episodes
            
        except Exception as e:
            raise ValueError(f"Failed to fetch RSS feed: {e}")
    
    def download_audio(self, audio_url, output_dir):
        """Download audio file from URL"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get filename from URL
        parsed_url = urlparse(audio_url)
        filename = Path(parsed_url.path).name
        if not filename or not any(filename.endswith(ext) for ext in ['.mp3', '.wav', '.m4a']):
            filename = f"episode_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        
        output_path = output_dir / filename
        
        # Skip if already downloaded
        if output_path.exists():
            print(f"✓ Audio already exists: {output_path}")
            return output_path
        
        print(f"Downloading audio: {filename}")
        
        try:
            # Add proper headers for Buzzsprout and other podcast hosts
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'audio/mpeg, audio/*, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'identity',
                'Connection': 'keep-alive',
                'Referer': 'https://www.buzzsprout.com/'
            }
            
            response = requests.get(audio_url, stream=True, headers=headers, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Simple progress indicator
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\rProgress: {progress:.1f}%", end='', flush=True)
            
            print(f"\n✓ Downloaded: {output_path}")
            return output_path
            
        except Exception as e:
            if output_path.exists():
                output_path.unlink()  # Clean up partial download
            raise ValueError(f"Failed to download audio: {e}")
    
    def transcribe_audio(self, audio_path, output_dir=None):
        """Transcribe audio file using Whisper"""
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        print(f"Transcribing: {audio_path.name}")
        
        # Transcribe with Whisper
        result = self.whisper_model.transcribe(
            str(audio_path),
            word_timestamps=True,
            verbose=False
        )
        
        # Prepare output
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True)
            transcript_file = output_dir / f"{audio_path.stem}_transcript.json"
        else:
            transcript_file = audio_path.parent / f"{audio_path.stem}_transcript.json"
        
        # Save transcript with timestamps
        transcript_data = {
            "file": str(audio_path),
            "duration": result.get("duration", 0),
            "language": result.get("language", "en"),
            "text": result["text"],
            "segments": result["segments"],
            "processed_at": datetime.now().isoformat()
        }
        
        with open(transcript_file, 'w') as f:
            json.dump(transcript_data, f, indent=2)
        
        print(f"✓ Transcript saved: {transcript_file}")
        return transcript_data
    
    def process_rss_feed(self, rss_url, output_dir="./output", max_episodes=1, skip_episodes=0):
        """Process latest episodes from RSS feed"""
        episodes = self.fetch_rss_episodes(rss_url, max_episodes, skip_episodes)
        
        results = []
        for episode in episodes:
            print(f"\n📻 Processing: {episode['title']}")
            
            try:
                # Create episode-specific directory
                episode_dir = Path(output_dir) / self.sanitize_filename(episode['title'])
                episode_dir.mkdir(parents=True, exist_ok=True)
                
                # Download audio
                audio_path = self.download_audio(episode['audio_url'], episode_dir)
                
                # Check if already processed
                transcript_file = episode_dir / f"{audio_path.stem}_transcript.json"
                if transcript_file.exists():
                    print(f"✓ Loading existing transcript")
                    with open(transcript_file, 'r') as f:
                        transcript_data = json.load(f)
                else:
                    # Transcribe
                    transcript_data = self.transcribe_audio(audio_path, episode_dir)
                
                # Detect hands
                hands_detected = self.detect_hands(transcript_data)
                
                # Generate report
                report_file = self.generate_report(
                    transcript_data, 
                    hands_detected, 
                    episode_dir / f"{audio_path.stem}_poker_hands.md"
                )
                
                # Save episode metadata
                episode_data = {
                    "episode": episode,
                    "audio_file": str(audio_path),
                    "transcript_file": str(transcript_file),
                    "report_file": str(report_file),
                    "hands_count": len(hands_detected),
                    "processed_at": datetime.now().isoformat()
                }
                
                with open(episode_dir / "episode_data.json", 'w') as f:
                    json.dump(episode_data, f, indent=2)
                
                results.append(episode_data)
                print(f"✅ Episode processed: {len(hands_detected)} hands detected")
                
            except Exception as e:
                print(f"❌ Failed to process episode: {e}")
                continue
        
        return results
    
    def sanitize_filename(self, filename):
        """Create safe filename from episode title"""
        import re
        # Remove/replace unsafe characters
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limit length
        return safe_name[:100]
    
    def detect_hands(self, transcript_data):
        """Detect poker hands in transcript with improved logic"""
        segments = transcript_data["segments"]
        
        hands_detected = []
        
        # Better patterns for actual hand analysis
        hand_start_patterns = [
            r"(?:i|we|he|she|they|villain|hero|player)\s+(?:have|had|got dealt|was dealt|held|pick up)\s+(?:pocket|hole cards?)",
            r"(?:with|holding|dealt)\s+(?:pocket|ace|king|queen|jack|\d+)",
            r"(?:preflop|pre-flop).*(?:raise|call|fold|all.?in)",
            r"(?:flop|turn|river)\s+(?:comes?|brings?|is|was)",
            r"board\s+(?:comes?|is|was|reads?)",
            r"hand\s+(?:analysis|breakdown|review|discussion)",
            r"(?:let's|we'll|i'll)\s+(?:talk about|discuss|analyze|break down|look at)\s+(?:this|a|the)\s+hand"
        ]
        
        # Cards and combinations that suggest actual hand details
        card_patterns = [
            r"(?:ace|king|queen|jack|\d+)(?:\s+of\s+(?:hearts|diamonds|clubs|spades))?",
            r"pocket\s+(?:aces|kings|queens|jacks|tens|nines|eights|sevens|sixes|fives|fours|threes|twos|deuces)",
            r"(?:suited|offsuit)\s+(?:ace|king|queen|jack)",
            r"(?:A|K|Q|J|T|\d)(?:s|h|d|c)?\s*(?:A|K|Q|J|T|\d)(?:s|h|d|c)?",
        ]
        
        # Action patterns that indicate hand progression
        action_patterns = [
            r"(?:raises?|calls?|folds?|checks?|bets?|all.?in|shoves?|jams?)\s+(?:to\s+)?\$?\d+",
            r"(?:three|3).?bet(?:s|ting)?",
            r"(?:four|4).?bet(?:s|ting)?",
            r"check.?raise",
            r"continuation\s+bet|c.?bet"
        ]
        
        import re
        
        for i, segment in enumerate(segments):
            segment_text = segment["text"]
            segment_lower = segment_text.lower()
            
            # Check for hand start indicators
            hand_start_score = 0
            for pattern in hand_start_patterns:
                if re.search(pattern, segment_lower):
                    hand_start_score += 2
            
            # Check for card mentions
            card_score = 0
            for pattern in card_patterns:
                matches = re.findall(pattern, segment_lower)
                card_score += len(matches)
            
            # Check for action descriptions
            action_score = 0
            for pattern in action_patterns:
                if re.search(pattern, segment_lower):
                    action_score += 1
            
            # Look at surrounding context (previous and next segments)
            context_score = 0
            context_window = []
            
            # Add previous segment
            if i > 0:
                context_window.append(segments[i-1]["text"])
            context_window.append(segment_text)
            # Add next segment
            if i < len(segments) - 1:
                context_window.append(segments[i+1]["text"])
            
            context_text = " ".join(context_window).lower()
            
            # Bonus points for multi-segment hand discussions
            if any(word in context_text for word in ["preflop", "flop", "turn", "river", "showdown"]):
                context_score += 1
            
            # Calculate total confidence
            total_score = hand_start_score + card_score + action_score + context_score
            
            # Only consider segments with substantial poker content
            if total_score >= 3 and (card_score >= 1 or hand_start_score >= 1):
                confidence = min(total_score / 8.0, 1.0)  # Normalize to 0-1
                
                hands_detected.append({
                    "timestamp": segment["start"],
                    "duration": segment["end"] - segment["start"],
                    "text": segment_text,
                    "confidence": confidence,
                    "scores": {
                        "hand_start": hand_start_score,
                        "cards": card_score,
                        "actions": action_score,
                        "context": context_score
                    }
                })
        
        # Sort by confidence (highest first)
        hands_detected.sort(key=lambda x: x["confidence"], reverse=True)
        
        print(f"✓ Detected {len(hands_detected)} potential poker hands")
        return hands_detected
    
    def generate_report(self, transcript_data, hands_detected, output_file=None):
        """Generate a readable report of detected hands"""
        if not output_file:
            audio_file = Path(transcript_data["file"])
            output_file = audio_file.parent / f"{audio_file.stem}_poker_hands.md"
        
        # Calculate average confidence
        avg_confidence = 0.00
        if hands_detected:
            avg_confidence = sum(h['confidence'] for h in hands_detected) / len(hands_detected)
        
        report_content = f"""# Poker Hands Analysis
        
**Source:** {transcript_data['file']}
**Duration:** {transcript_data['duration']:.1f} seconds
**Language:** {transcript_data['language']}
**Processed:** {transcript_data['processed_at']}

## Summary
- **Total hands detected:** {len(hands_detected)}
- **Average confidence:** {avg_confidence:.2f}

## Detected Hands

"""
        
        for i, hand in enumerate(hands_detected, 1):
            timestamp_min = int(hand['timestamp'] // 60)
            timestamp_sec = int(hand['timestamp'] % 60)
            
            report_content += f"""### Hand {i}
**Timestamp:** {timestamp_min}:{timestamp_sec:02d}
**Confidence:** {hand['confidence']:.2f}
**Text:** {hand['text'].strip()}

---

"""
        
        with open(output_file, 'w') as f:
            f.write(report_content)
        
        print(f"✓ Report saved: {output_file}")
        return output_file

def main():
    parser = argparse.ArgumentParser(description="Analyze poker hands from podcast RSS feeds")
    
    # Main input - either RSS feed or audio file
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--rss", help="RSS feed URL")
    group.add_argument("--audio-file", help="Path to audio file")
    
    # Common options
    parser.add_argument("--model", default="medium", choices=whisper.available_models(),
                       help="Whisper model size (default: medium)")
    parser.add_argument("--output-dir", default="./output", help="Output directory for results")
    parser.add_argument("--max-episodes", type=int, default=1,
                       help="Max episodes to process from RSS (default: 1)")
    parser.add_argument("--skip-episodes", type=int, default=0,
                       help="Number of episodes to skip (default: 0)")
    parser.add_argument("--skip-transcription", action="store_true",
                       help="Skip transcription if transcript file exists")
    
    args = parser.parse_args()
    
    try:
        analyzer = PokerHandAnalyzer(model_size=args.model)
        
        if args.rss:
            # Process RSS feed
            results = analyzer.process_rss_feed(
                args.rss, 
                args.output_dir, 
                args.max_episodes,
                args.skip_episodes
            )
            
            print(f"\n🃏 RSS Processing complete!")
            print(f"📺 Processed {len(results)} episodes")
            total_hands = sum(r['hands_count'] for r in results)
            print(f"🎯 Total hands found: {total_hands}")
            
        else:
            # Process single audio file (original functionality)
            audio_path = Path(args.audio_file)
            expected_transcript = audio_path.parent / f"{audio_path.stem}_transcript.json"
            
            if args.skip_transcription and expected_transcript.exists():
                print(f"Loading existing transcript: {expected_transcript}")
                with open(expected_transcript, 'r') as f:
                    transcript_data = json.load(f)
            else:
                transcript_data = analyzer.transcribe_audio(args.audio_file, args.output_dir)
            
            hands_detected = analyzer.detect_hands(transcript_data)
            output_file = analyzer.generate_report(transcript_data, hands_detected)
            
            print(f"\n🃏 Analysis complete!")
            print(f"📄 Report: {output_file}")
            print(f"🎯 Found {len(hands_detected)} potential poker hands")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()