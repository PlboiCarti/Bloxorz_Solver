
# AGENTS.md — Bloxorz 3D

## 1. Project overview

This is a university AI project implementing the Bloxorz puzzle
game with a 3D graphical interface and search algorithms.

- Frontend: Three.js and JavaScript.
- Backend: Python game engine and search algorithms.
- The GUI communicates with Python through a thin API adapter.
- Python game code lives in `game/`; the HTTP adapter is `server.py`; the
  browser GUI is `gui/index.html`; project guidance and API documents live in
  `docs/`.

## 2. Architecture rules

- Keep the GUI separate from game logic and search algorithms.
- Python is the source of truth for game state, legal moves,
  winning conditions, and special tile mechanics.
- The GUI is responsible for rendering, user input, animations, and controls.
  It may present Engine outcomes as UI modes such as `WON` or `LOST`; these
  labels are not game-state fields owned by Python.
- Use a dedicated API adapter to communicate with the backend.
- Do not implement a second copy of the search algorithms
  in JavaScript.
- Do not change API schemas without checking their impact
  on both frontend and backend.

### Code flows and responsibility boundaries

Keep the project organized as distinct flows. Use separate modules/files
when practical; if the current prototype keeps code together, preserve clear
sections and APIs between these responsibilities:

1. **UI and input flow:** buttons, keyboard input, status/error messages,
   and playback controls. This flow sends user intent to the frontend API
   adapter and does not decide game rules.
2. **Frontend API flow:** owns HTTP requests, request/response conversion,
   and connection errors. It is the only frontend flow that calls Python.
3. **Backend game flow:** owns the board, state, legal moves, transitions,
   goal checks, falls, and special-tile mechanics. The GUI displays those
   outcomes as modes but does not decide them.
4. **Search flow:** owns BFS, DFS, UCS, A*, their costs/heuristics, and
   solution reconstruction. It calls the backend game model and does not
   depend on GUI or Three.js code.
5. **Rendering and animation flow:** owns Three.js scene construction,
   tile/block visuals, camera, and animation. It displays backend state and
   plays accepted transitions; it must not independently accept/reject moves.

Keep boundaries explicit: user input → API adapter → Python game → response →
renderer. Search is a separate backend flow; the GUI invokes it through
POST /solve and replays each returned action through POST /transition. Do not
couple rendering to HTTP details or duplicate backend rules in the UI.

### Current integration constraints

- The browser calls Python only through the HTTP adapter in `server.py`.
- `game.State.occupied_cells()` is internal to Python. The server derives it
  when validating board bounds; the HTTP state does not carry this field.
- The GUI places the ordinary block using `block_position` and `orientation`,
  and places split cubes using `cube1_position` / `cube2_position`.
- Solver controls are integrated with /solve; replay must apply every action through
  /transition. Keep Python as the source of truth for all resulting states.
- Solver requests run in worker threads with cooperative cancellation at search and
  H2 preprocessing checkpoints. Peak-memory measurement is serialized because
  `tracemalloc` is process-global.

## 3. GUI requirements

- Render the board, floor tiles, goal, and the 1x1x2 block.
- Support standing, horizontal, and vertical block orientations.
- Animate rolling around the correct pivot edge.
- Support keyboard and GUI-button controls.
- Provide New Game, Restart, manual movement, solver selection, and replay
  controls. Solver paths come from /solve; replay transitions go through Python.
- Display backend errors and rejected moves clearly.

## 4. Special tiles

The GUI must be able to represent:

- Fragile tiles.
- Open and closed bridges.
- Soft switches.
- Heavy switches.
- Split switches.
- Two separate unit cubes and their rejoining state.

Render special tile states according to the state returned
by the game engine. Do not assume a visual effect means that
the underlying game mechanic has been implemented.

## 5. Coding rules

- Inspect the existing project before changing files.
- Follow existing naming conventions and code structure.
- Prefer small, focused changes over large rewrites.
- Reuse existing components where reasonable.
- Do not introduce dependencies without explaining why.
- Do not remove existing functionality unless requested.
- Keep rendering, animation, API communication, and UI
  controls in separate modules when practical.
- For every project change, update `README.md` with any changed behavior,
  setup, controls, API, or architecture information relevant to users.
- For every project change, append a dated entry to `docs/CHANGELOG.md` describing
  the files/flows changed, the result, and checks actually performed. Record
  when checks were not run; never imply unverified behavior was tested.
- Apply this documentation rule to code, configuration, UI, API, and
  documentation-only changes. Keep the README focused on current usage and
  architecture; keep the chronological change record in `docs/CHANGELOG.md`.

## 6. Testing and reporting

- Test every new or modified behavior where practical.
- Check boundary moves, rejected moves, and animation completion.
- Test the API adapter against the actual backend contract.
- State which tests were run and their actual results.
- Never claim that a feature works if it has not been verified.

## 7. Before making changes

For non-trivial tasks:
1. Inspect relevant files.
2. Explain the implementation plan briefly.
3. Identify files that will be changed.
4. Implement the smallest suitable solution.
5. Run relevant checks and summarize the results.

Ask for approval before destructive changes, major architectural
changes, or adding dependencies that significantly affect the project.
