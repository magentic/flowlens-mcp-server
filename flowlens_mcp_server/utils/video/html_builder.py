import json
from typing import List
from dataclasses import dataclass


@dataclass
class BuilderParams:
    """Parameters for building HTML content for rrweb player."""
    events: List
    video_width: int
    video_height: int


class HtmlBuilder:
    """Builder class for generating HTML content with embedded rrweb player."""

    def __init__(self, params: BuilderParams):
        self._params = params

    def build(self, show_controller: bool) -> str:
        """
        Build HTML content based on controller visibility preference.

        Args:
            show_controller: If True, generates HTML with custom controller.
                           If False, generates minimal HTML without controller.

        Returns:
            The complete HTML string.
        """
        if show_controller:
            return self._generate_html_with_controller()
        else:
            return self._generate_html_without_controller()

    def _generate_html_with_controller(self) -> str:
        """
        Generate HTML content with rrweb events embedded directly and custom controller.
        Includes play/pause button, progress bar, and time display.
        Returns the HTML string (not a file path).
        """
        # Escape </script> tags in JSON to prevent premature script closing
        events_json = json.dumps(self._params.events).replace('</script>', '<\\/script>')

        html_content = f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <link href="https://cdn.jsdelivr.net/npm/rrweb-player@latest/dist/style.css" rel="stylesheet" />
    <script src="https://cdn.jsdelivr.net/npm/rrweb-player@latest/dist/index.js"></script>
    <style>
      html, body {{padding: 0; border: none; margin: 0; overflow: hidden;}}
      #player-container {{position: relative; width: 100%; height: 100%;}}
      #custom-controls {{
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: rgba(0, 0, 0, 0.8);
        padding: 10px 15px;
        display: flex;
        align-items: center;
        gap: 15px;
        z-index: 9999;
      }}
      #play-pause-btn {{
        background: #fff;
        border: none;
        border-radius: 4px;
        width: 36px;
        height: 36px;
        cursor: pointer;
        font-size: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
      }}
      #play-pause-btn:hover {{
        background: #e0e0e0;
      }}
      #progress-container {{
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 5px;
      }}
      #progress-bar {{
        width: 100%;
        height: 6px;
        background: rgba(255, 255, 255, 0.3);
        border-radius: 3px;
        cursor: pointer;
        position: relative;
      }}
      #progress-fill {{
        height: 100%;
        background: #4CAF50;
        border-radius: 3px;
        width: 0%;
        transition: width 0.1s linear;
      }}
      #time-display {{
        color: #fff;
        font-family: monospace;
        font-size: 12px;
        text-align: center;
      }}
    </style>
  </head>
  <body>
    <div id="player-container"></div>
    <div id="custom-controls">
      <button id="play-pause-btn" title="Play/Pause">▶</button>
      <div id="progress-container">
        <div id="progress-bar">
          <div id="progress-fill"></div>
        </div>
        <div id="time-display">00:00 / 00:00</div>
      </div>
    </div>
    <script>
      /*<!--*/
      const events = {events_json};
      /*-->*/

      // Calculate total duration from events
      const totalDuration = events.length > 0 ? events[events.length - 1].timestamp - events[0].timestamp : 0;

      const userConfig = {{width: {self._params.video_width}, height: {self._params.video_height}}};
      window.replayer = new rrwebPlayer({{
        events,
        target: document.getElementById('player-container'),
        width: userConfig.width,
        height: userConfig.height,
        props: {{
          ...userConfig,
          events,
          showController: false,  // Disable default controller
          autoPlay: true,
          skipInactive: true,
        }}
      }});

      // Custom controls state
      let isPlaying = true;
      let currentTime = 0;

      // Get DOM elements
      const playPauseBtn = document.getElementById('play-pause-btn');
      const progressBar = document.getElementById('progress-bar');
      const progressFill = document.getElementById('progress-fill');
      const timeDisplay = document.getElementById('time-display');

      // Format time in mm:ss
      function formatTime(ms) {{
        const totalSeconds = Math.floor(ms / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${{String(minutes).padStart(2, '0')}}:${{String(seconds).padStart(2, '0')}}`;
      }}

      // Update progress display
      function updateProgress(time) {{
        currentTime = time;
        const progress = totalDuration > 0 ? (time / totalDuration) * 100 : 0;
        progressFill.style.width = `${{progress}}%`;
        timeDisplay.textContent = `${{formatTime(time)}} / ${{formatTime(totalDuration)}}`;
      }}

      // Play/Pause button handler
      playPauseBtn.addEventListener('click', () => {{
        if (isPlaying) {{
          window.replayer.pause();
          playPauseBtn.textContent = '▶';
          isPlaying = false;
        }} else {{
          window.replayer.play();
          playPauseBtn.textContent = '⏸';
          isPlaying = true;
        }}
      }});

      // Progress bar seek handler
      progressBar.addEventListener('click', (e) => {{
        const rect = progressBar.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const percentage = clickX / rect.width;
        const seekTime = percentage * totalDuration;
        window.replayer.goto(seekTime);
        updateProgress(seekTime);
      }});

      // Event listeners
      window.replayer.addEventListener('start', () => {{
        if (window.onReplayStart) window.onReplayStart();
        playPauseBtn.textContent = '⏸';
        isPlaying = true;
      }});

      window.replayer.addEventListener('finish', () => {{
        if (window.onReplayFinish) window.onReplayFinish();
        playPauseBtn.textContent = '▶';
        isPlaying = false;
      }});

      window.replayer.addEventListener('ui-update-current-time', (payload) => {{
        const time = payload.payload || 0;
        updateProgress(time);
        // Notify Python about time update for synchronization
        if (window.onTimeUpdate) window.onTimeUpdate(time);
      }});
    </script>
  </body>
</html>"""

        print("📝 Generated HTML content for rrweb replay with controller")
        return html_content

    def _generate_html_without_controller(self) -> str:
        """
        Generate HTML content with rrweb events embedded directly without custom controller.
        Minimal HTML structure with only the rrweb player, no custom controls.
        Returns the HTML string (not a file path).
        """
        # Escape </script> tags in JSON to prevent premature script closing
        events_json = json.dumps(self._params.events).replace('</script>', '<\\/script>')

        html_content = f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <link href="https://cdn.jsdelivr.net/npm/rrweb-player@latest/dist/style.css" rel="stylesheet" />
    <script src="https://cdn.jsdelivr.net/npm/rrweb-player@latest/dist/index.js"></script>
    <style>
      html, body {{padding: 0; border: none; margin: 0; overflow: hidden;}}
      #player-container {{position: relative; width: 100%; height: 100%;}}
    </style>
  </head>
  <body>
    <div id="player-container"></div>
    <script>
      /*<!--*/
      const events = {events_json};
      /*-->*/

      const userConfig = {{width: {self._params.video_width}, height: {self._params.video_height}}};
      window.replayer = new rrwebPlayer({{
        events,
        target: document.getElementById('player-container'),
        width: userConfig.width,
        height: userConfig.height,
        props: {{
          ...userConfig,
          events,
          showController: false,  // Disable default controller
          autoPlay: true,
          skipInactive: true,
        }}
      }});

      // Event listeners for synchronization with Python
      window.replayer.addEventListener('start', () => {{
        if (window.onReplayStart) window.onReplayStart();
      }});

      window.replayer.addEventListener('finish', () => {{
        if (window.onReplayFinish) window.onReplayFinish();
      }});

      window.replayer.addEventListener('ui-update-current-time', (payload) => {{
        const time = payload.payload || 0;
        // Notify Python about time update for synchronization
        if (window.onTimeUpdate) window.onTimeUpdate(time);
      }});
    </script>
  </body>
</html>"""

        print("📝 Generated HTML content for rrweb replay without controller")
        return html_content
