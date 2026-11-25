(function () {
  "use strict";

  const DATA = window.MDP_DATA;
  if (!DATA) {
    document.body.innerHTML = "<p style='padding:40px;font-size:24px'>Không tìm thấy dữ liệu web/data.js. Hãy chạy <code>python export_web_data.py</code>.</p>";
    return;
  }

  const AUDIO_META = window.MDP_AUDIO || null;
  const GAP_MS = (AUDIO_META && AUDIO_META.gapMs) || 1200;
  const FALLBACK_DURS = {
    s1a: 26000,
    s1b: 24000,
    s2: 45000,
    s3: 55000,
    s4: 48000,
    s5: 48000,
    s6: 54000,
  };

  function segDurationMs(key) {
    const metaSeg = AUDIO_META && AUDIO_META.segments && AUDIO_META.segments[key];
    return (metaSeg && metaSeg.durationMs) || FALLBACK_DURS[key] || 30000;
  }

  function segSrc(key) {
    const metaSeg = AUDIO_META && AUDIO_META.segments && AUDIO_META.segments[key];
    return (metaSeg && metaSeg.src) || null;
  }

  // ===================== TIỆN ÍCH CHUNG =====================
  const SVG_NS = "http://www.w3.org/2000/svg";
  const ACTION_VEC = {
    0: [0, -1],  // Lên
    1: [0, 1],   // Xuống
    2: [-1, 0],  // Trái
    3: [1, 0],   // Phải
  };
  const HEADING_DEG = { 0: 0, 1: 180, 2: -90, 3: 90 };

  function stateToRC(s) {
    return [Math.floor(s / 4) + 1, (s % 4) + 1];
  }

  function rcToState(r, c) {
    return (r - 1) * 4 + (c - 1);
  }

  function svgEl(tag, attrs) {
    const el = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      el.setAttribute(k, String(v));
    }
    return el;
  }

  function lerpColor(c1, c2, t) {
    const r = Math.round(c1[0] + (c2[0] - c1[0]) * t);
    const g = Math.round(c1[1] + (c2[1] - c1[1]) * t);
    const b = Math.round(c1[2] + (c2[2] - c1[2]) * t);
    return `rgb(${r}, ${g}, ${b})`;
  }

  function heatColor(v) {
    if (v <= 0) return "#FFFFFF";
    const t = Math.max(0, Math.min(1, v / 8.0));
    if (t < 0.25) {
      return lerpColor([255, 255, 255], [204, 251, 241], t / 0.25);
    }
    return lerpColor([204, 251, 241], [15, 118, 110], (t - 0.25) / 0.75);
  }

  function fmtPct(rate) {
    return (rate * 100).toFixed(1) + "%";
  }

  // ===================== LỚP LƯỚI TÁI SỬ DỤNG =====================
  class GridView {
    constructor(container, { size = 640, showAxes = true, compact = false } = {}) {
      this.container = container;
      this.size = size;
      this.cellSize = size / 4;
      this.compact = compact;

      this.wrapper = document.createElement("div");
      this.wrapper.className = "grid-wrapper" + (compact ? " compact" : "");

      const middle = document.createElement("div");
      middle.className = "grid-middle";

      if (showAxes) {
        const yAxis = document.createElement("div");
        yAxis.className = "y-axis";
        yAxis.style.height = `${size}px`;
        for (let r = 4; r >= 1; r--) {
          const lbl = document.createElement("div");
          lbl.textContent = `H${r}`;
          yAxis.appendChild(lbl);
        }
        middle.appendChild(yAxis);
      }

      this.board = document.createElement("div");
      this.board.className = "grid-board";
      this.board.style.width = `${size}px`;
      this.board.style.height = `${size}px`;

      this.cellsGrid = document.createElement("div");
      this.cellsGrid.className = "grid-cells";

      this.cells = new Array(16);
      for (let r = 4; r >= 1; r--) {
        for (let c = 1; c <= 4; c++) {
          const s = rcToState(r, c);
          const cell = document.createElement("div");
          cell.className = "grid-cell";

          if (r === 1 && c === 1) cell.classList.add("start");
          if (r === 4 && c === 4) cell.classList.add("goal");
          if ((r === 3 && c === 3) || (r === 2 && c === 3)) cell.classList.add("trap");

          const coord = document.createElement("span");
          coord.className = "cell-coord";
          coord.textContent = `(${c},${r})`;
          cell.appendChild(coord);

          const body = document.createElement("div");
          body.className = "cell-body";
          body.style.display = "flex";
          body.style.flexDirection = "column";
          body.style.alignItems = "center";
          cell.appendChild(body);

          this.cellsGrid.appendChild(cell);
          this.cells[s] = { el: cell, body, r, c, s };
        }
      }

      this.svg = svgEl("svg", {
        class: "grid-svg",
        viewBox: `0 0 ${size} ${size}`,
        width: size,
        height: size,
      });

      this.pathLayer = svgEl("g", {});
      this.arrowLayer = svgEl("g", {});
      this.slipLayer = svgEl("g", {});
      this.svg.appendChild(this.pathLayer);
      this.svg.appendChild(this.arrowLayer);
      this.svg.appendChild(this.slipLayer);

      this.robot = document.createElement("div");
      this.robot.className = "robot-token" + (compact ? " compact" : "");
      this.robot.style.display = "none";
      const notch = document.createElement("div");
      notch.className = "robot-notch";
      this.robot.appendChild(notch);

      this.board.appendChild(this.cellsGrid);
      this.board.appendChild(this.svg);
      this.board.appendChild(this.robot);
      middle.appendChild(this.board);
      this.wrapper.appendChild(middle);

      if (showAxes) {
        const xAxis = document.createElement("div");
        xAxis.className = "x-axis";
        xAxis.style.width = `${size}px`;
        xAxis.style.marginLeft = "auto";
        for (let c = 1; c <= 4; c++) {
          const lbl = document.createElement("div");
          lbl.textContent = `Cột ${c}`;
          xAxis.appendChild(lbl);
        }
        this.wrapper.appendChild(xAxis);
      }

      this.container.appendChild(this.wrapper);
      this._renderStaticBadges();
    }

    cellCenter(s) {
      const [r, c] = stateToRC(s);
      return {
        x: (c - 0.5) * this.cellSize,
        y: (4 - r + 0.5) * this.cellSize,
      };
    }

    _renderStaticBadges() {
      for (let s = 0; s < 16; s++) {
        const { r, c, body } = this.cells[s];
        body.innerHTML = "";
        if (r === 1 && c === 1) {
          const b = document.createElement("div");
          b.className = "cell-badge start";
          b.textContent = "START";
          body.appendChild(b);
        } else if (r === 4 && c === 4) {
          const b = document.createElement("div");
          b.className = "cell-badge goal";
          b.textContent = "ĐÍCH";
          const rw = document.createElement("div");
          rw.className = "cell-reward goal";
          rw.textContent = "+10";
          body.appendChild(b);
          body.appendChild(rw);
        } else if ((r === 3 && c === 3) || (r === 2 && c === 3)) {
          const b = document.createElement("div");
          b.className = "cell-badge trap";
          b.textContent = "BẪY";
          const rw = document.createElement("div");
          rw.className = "cell-reward trap";
          rw.textContent = "−10";
          body.appendChild(b);
          body.appendChild(rw);
        }
      }
    }

    setCellValues(V, showHeatmap = false, { smallCorner = false } = {}) {
      for (let s = 0; s < 16; s++) {
        const { el, body, r, c } = this.cells[s];
        el.classList.remove("dark-text");
        const isGoal = r === 4 && c === 4;
        const isTrap = (r === 3 && c === 3) || (r === 2 && c === 3);

        if (!isGoal && !isTrap) {
          if (showHeatmap && V) {
            const val = V[s];
            el.style.backgroundColor = heatColor(val);
            if (val > 4.2) el.classList.add("dark-text");
          } else {
            el.style.backgroundColor = (r === 1 && c === 1) ? "#EFF6FF" : "#FFFFFF";
          }
        }

        const oldVal = el.querySelector(".cell-value");
        if (oldVal) oldVal.remove();

        if (V && !isGoal && !isTrap) {
          const vEl = document.createElement("div");
          vEl.className = "cell-value" + (smallCorner ? " small-corner" : "");
          vEl.textContent = V[s].toFixed(2);
          if (smallCorner) {
            el.appendChild(vEl);
          } else {
            body.innerHTML = "";
            if (r === 1 && c === 1) {
              const st = document.createElement("div");
              st.className = "cell-badge start";
              st.style.fontSize = "14px";
              st.style.marginBottom = "2px";
              st.textContent = "START";
              body.appendChild(st);
            }
            body.appendChild(vEl);
          }
        } else if (!V && !isGoal && !isTrap) {
          this._renderCellDefault(s);
        }
      }
    }

    _renderCellDefault(s) {
      const { body, r, c } = this.cells[s];
      body.innerHTML = "";
      if (r === 1 && c === 1) {
        const b = document.createElement("div");
        b.className = "cell-badge start";
        b.textContent = "START";
        body.appendChild(b);
      }
    }

    setFocusCells(indices) {
      for (let s = 0; s < 16; s++) {
        this.cells[s].el.classList.toggle("focus-ring", indices.includes(s));
      }
    }

    setChangedCells(changedIndices) {
      for (let s = 0; s < 16; s++) {
        this.cells[s].el.classList.toggle("changed", changedIndices.includes(s));
      }
    }

    setPolicy(policy, { color = "#1D4ED8", arrowScale = 1, opacity = 1 } = {}) {
      this.arrowLayer.innerHTML = "";
      this.cellsGrid.classList.toggle("has-arrows", Boolean(policy));
      if (!policy) return;

      const len = this.cellSize * 0.25 * arrowScale;
      const head = this.cellSize * 0.1 * arrowScale;

      this.arrowLayer.setAttribute("opacity", String(opacity));
      for (let s = 0; s < 16; s++) {
        const [r, c] = stateToRC(s);
        if ((r === 4 && c === 4) || (r === 3 && c === 3) || (r === 2 && c === 3)) continue;

        const a = policy[s];
        const [dx, dy] = ACTION_VEC[a];
        const { x, y } = this.cellCenter(s);

        const x1 = x - dx * len * 0.7;
        const y1 = y - dy * len * 0.7;
        const x2 = x + dx * len;
        const y2 = y + dy * len;

        this._drawSvgArrow(this.arrowLayer, x1, y1, x2, y2, color, this.compact ? 4 : 5, head);
      }
    }

    _drawSvgArrow(layer, x1, y1, x2, y2, color, strokeWidth, headSize) {
      const angle = Math.atan2(y2 - y1, x2 - x1);
      const lineEndX = x2 - Math.cos(angle) * headSize * 0.65;
      const lineEndY = y2 - Math.sin(angle) * headSize * 0.65;

      layer.appendChild(svgEl("line", {
        x1, y1, x2: lineEndX, y2: lineEndY,
        stroke: color,
        "stroke-width": strokeWidth,
        "stroke-linecap": "round",
      }));

      const p1 = `${x2},${y2}`;
      const p2 = `${x2 - headSize * Math.cos(angle - Math.PI / 6)},${y2 - headSize * Math.sin(angle - Math.PI / 6)}`;
      const p3 = `${x2 - headSize * Math.cos(angle + Math.PI / 6)},${y2 - headSize * Math.sin(angle + Math.PI / 6)}`;
      layer.appendChild(svgEl("polygon", {
        points: `${p1} ${p2} ${p3}`,
        fill: color,
      }));
    }

    drawPath(states, { color = "#16A34A", dashed = false, width = 6, opacity = 0.9, layerId = "default", halo = false } = {}) {
      this.pathLayer.querySelectorAll(`[data-layer-id="${layerId}"]`).forEach((n) => n.remove());
      if (!states || states.length < 2) return;

      const pts = states.map((s) => {
        const { x, y } = this.cellCenter(s);
        return `${x},${y}`;
      }).join(" ");

      if (halo) {
        const haloPoly = svgEl("polyline", {
          points: pts,
          fill: "none",
          stroke: "#FFFFFF",
          "stroke-width": width + 6,
          "stroke-linecap": "round",
          "stroke-linejoin": "round",
          "stroke-opacity": 0.9,
          "data-layer-id": layerId,
        });
        if (dashed) {
          haloPoly.setAttribute("stroke-dasharray", "12 10");
        }
        this.pathLayer.appendChild(haloPoly);
      }

      const poly = svgEl("polyline", {
        points: pts,
        fill: "none",
        stroke: color,
        "stroke-width": width,
        "stroke-linecap": "round",
        "stroke-linejoin": "round",
        "stroke-opacity": opacity,
        "data-layer-id": layerId,
      });
      if (dashed) {
        poly.setAttribute("stroke-dasharray", "12 10");
      }
      this.pathLayer.appendChild(poly);
    }

    clearPaths() {
      this.pathLayer.innerHTML = "";
    }

    moveRobot(s, heading = 0, instant = false) {
      const { x, y } = this.cellCenter(s);
      if (instant) {
        this.robot.style.transition = "none";
      } else {
        this.robot.style.transition = "";
      }
      this.robot.style.display = "flex";
      this.robot.style.left = `${x}px`;
      this.robot.style.top = `${y}px`;
      this.robot.style.transform = `rotate(${HEADING_DEG[heading] || 0}deg)`;
      if (instant) {
        void this.robot.offsetWidth;
        this.robot.style.transition = "";
      }
    }

    hideRobot() {
      this.robot.style.display = "none";
    }

    flashCell(s, kind) {
      const el = this.cells[s].el;
      const cls = kind === "goal" ? "flash-goal" : "flash-trap";
      el.classList.add(cls);
      return cls;
    }

    clearFlashes() {
      for (const c of this.cells) {
        c.el.classList.remove("flash-trap", "flash-goal", "changed", "focus-ring");
      }
    }

    showSlipDemo(show) {
      this.slipLayer.innerHTML = "";
      if (!show) return;
      const { x, y } = this.cellCenter(0);

      this._drawSvgArrow(this.slipLayer, x, y - 28, x, y - 125, "#16A34A", 7, 16);
      const tMain = svgEl("text", {
        x: x + 16, y: y - 92,
        fill: "#15803D", "font-size": 24, "font-weight": 800,
      });
      tMain.textContent = "80% thẳng";
      this.slipLayer.appendChild(tMain);

      this._drawSvgArrow(this.slipLayer, x + 28, y, x + 115, y, "#F59E0B", 4, 12);
      const tRight = svgEl("text", {
        x: x + 56, y: y - 14,
        fill: "#B45309", "font-size": 20, "font-weight": 700,
      });
      tRight.textContent = "10% trượt";
      this.slipLayer.appendChild(tRight);

      this._drawSvgArrow(this.slipLayer, x - 26, y, x - 72, y, "#F59E0B", 4, 11);
      const tLeft = svgEl("text", {
        x: x - 74, y: y - 14,
        fill: "#B45309", "font-size": 19, "font-weight": 700,
      });
      tLeft.textContent = "10%";
      this.slipLayer.appendChild(tLeft);
    }

    clear() {
      this.clearPaths();
      this.arrowLayer.innerHTML = "";
      this.cellsGrid.classList.remove("has-arrows");
      this.slipLayer.innerHTML = "";
      this.clearFlashes();
      this.setCellValues(null, false);
      this._renderStaticBadges();
      this.hideRobot();
    }
  }

  // ===================== BỘ LẬP LỊCH THỐNG NHẤT =====================
  class Scheduler {
    constructor() {
      this.timers = new Set();
      this.paused = false;
    }

    after(ms, fn) {
      const item = { id: null, fn, remaining: ms, start: performance.now(), done: false };
      this.timers.add(item);
      if (!this.paused) {
        item.id = setTimeout(() => {
          item.done = true;
          this.timers.delete(item);
          fn();
        }, ms);
      }
      return item;
    }

    pause() {
      if (this.paused) return;
      this.paused = true;
      const now = performance.now();
      for (const item of this.timers) {
        if (item.id !== null) {
          clearTimeout(item.id);
          item.id = null;
          item.remaining = Math.max(0, item.remaining - (now - item.start));
        }
      }
    }

    resume() {
      if (!this.paused) return;
      this.paused = false;
      const now = performance.now();
      for (const item of [...this.timers]) {
        if (!item.done && item.id === null) {
          item.start = now;
          item.id = setTimeout(() => {
            item.done = true;
            this.timers.delete(item);
            item.fn();
          }, item.remaining);
        }
      }
    }

    clearAll() {
      for (const item of this.timers) {
        if (item.id !== null) clearTimeout(item.id);
        item.done = true;
      }
      this.timers.clear();
    }
  }

  // ===================== ĐỒ THỊ HỘI TỤ SVG (CẢNH 3) =====================
  function buildConvergenceChart(container, deltas, theta) {
    const W = 620;
    const H = 250;
    const pad = { l: 74, r: 24, t: 20, b: 44 };
    const pw = W - pad.l - pad.r;
    const ph = H - pad.t - pad.b;

    const minExp = -5;
    const maxExp = 1;
    const yFromVal = (val) => {
      const logV = Math.max(minExp, Math.min(maxExp, Math.log10(Math.max(1e-6, val))));
      return pad.t + ((maxExp - logV) / (maxExp - minExp)) * ph;
    };
    const xFromIdx = (idx) => pad.l + (idx / (deltas.length - 1)) * pw;

    const svg = svgEl("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}` });

    for (let e = minExp; e <= maxExp; e += 2) {
      const y = yFromVal(Math.pow(10, e));
      svg.appendChild(svgEl("line", { x1: pad.l, y1: y, x2: W - pad.r, y2: y, stroke: "#E5E7EB", "stroke-width": 1 }));
      const lbl = svgEl("text", { x: pad.l - 10, y: y + 5, "text-anchor": "end", fill: "#6B7280", "font-size": 14, "font-weight": 600 });
      lbl.textContent = `10^${e}`;
      svg.appendChild(lbl);
    }

    const yTheta = yFromVal(theta);
    svg.appendChild(svgEl("line", {
      x1: pad.l, y1: yTheta, x2: W - pad.r, y2: yTheta,
      stroke: "#EF4444", "stroke-width": 2, "stroke-dasharray": "8 6",
    }));
    const tLbl = svgEl("text", { x: W - pad.r - 4, y: yTheta - 8, "text-anchor": "end", fill: "#DC2626", "font-size": 14, "font-weight": 700 });
    tLbl.textContent = "Ngưỡng θ = 10⁻⁴";
    svg.appendChild(tLbl);

    const pts = deltas.map((d, i) => `${xFromIdx(i)},${yFromVal(d)}`).join(" ");
    svg.appendChild(svgEl("polyline", { points: pts, fill: "none", stroke: "#CBD5E1", "stroke-width": 2.5 }));

    const activeLine = svgEl("polyline", { points: "", fill: "none", stroke: "#2563EB", "stroke-width": 3.5, "stroke-linecap": "round" });
    svg.appendChild(activeLine);

    const marker = svgEl("circle", { cx: pad.l, cy: yFromVal(deltas[0]), r: 7, fill: "#2563EB", stroke: "#FFFFFF", "stroke-width": 2.5 });
    svg.appendChild(marker);

    const xLbl = svgEl("text", { x: pad.l + pw / 2, y: H - 6, "text-anchor": "middle", fill: "#6B7280", "font-size": 15, "font-weight": 600 });
    xLbl.textContent = "Vòng lặp Bellman (1 → 48)";
    svg.appendChild(xLbl);

    container.appendChild(svg);

    return function updateMarker(k) {
      if (k <= 0) {
        activeLine.setAttribute("points", "");
        marker.setAttribute("cx", xFromIdx(0));
        marker.setAttribute("cy", yFromVal(deltas[0]));
        return;
      }
      const idx = Math.min(k - 1, deltas.length - 1);
      const subPts = deltas.slice(0, idx + 1).map((d, i) => `${xFromIdx(i)},${yFromVal(d)}`).join(" ");
      activeLine.setAttribute("points", subPts);
      marker.setAttribute("cx", xFromIdx(idx));
      marker.setAttribute("cy", yFromVal(deltas[idx]));
    };
  }

  // ===================== 6 CẢNH DEMO =====================
  function createScenes(stageBody, scheduler, onSceneDone, goToScene) {
    // 1. Môi trường MDP (Beat 0 = s1a, Beat 1 = s1b)
    function scene1() {
      let grid = null;
      let beat = 0;
      let noteEl = null;

      function scheduleBeat1Highlights() {
        grid.setFocusCells([0]); // START (1,1)
        scheduler.after(5500, () => {
          if (beat !== 0) return;
          grid.setFocusCells([15]); // ĐÍCH (4,4)
        });
        scheduler.after(11500, () => {
          if (beat !== 0) return;
          grid.setFocusCells([10, 6]); // BẪY (3,3) & (3,2)
        });
        scheduler.after(18000, () => {
          if (beat !== 0) return;
          grid.setFocusCells([]);
        });
      }

      return {
        enter() {
          beat = 0;
          stageBody.innerHTML = `
            <div class="split-layout">
              <div class="left-col" id="s1-grid"></div>
              <div class="right-col">
                <div class="card">
                  <h2 class="scene-heading">1. Mô hình hóa MDP trên GridWorld 4x4</h2>
                  <p class="scene-subtitle">Bài toán tìm đường trong môi trường có yếu tố ngẫu nhiên.</p>
                  <ul class="bullet-list">
                    <li class="bullet-item"><span class="bullet-dot"></span><span><strong>S (Trạng thái):</strong> 16 ô lưới từ (1,1) đến (4,4).</span></li>
                    <li class="bullet-item"><span class="bullet-dot"></span><span><strong>A (Hành động):</strong> { Lên, Xuống, Trái, Phải }.</span></li>
                    <li class="bullet-item"><span class="bullet-dot"></span><span><strong>R (Phần thưởng):</strong> Đích +10, Bẫy −10, mỗi bước −0.04 (va tường −0.2).</span></li>
                    <li class="bullet-item"><span class="bullet-dot"></span><span><strong>γ = 0.99:</strong> Ưu tiên phần thưởng dài hạn.</span></li>
                  </ul>
                  <div id="s1-note" class="highlight-box">Nhấn Space để xem động lực ngẫu nhiên 80 / 10 / 10.</div>
                </div>
              </div>
            </div>
          `;
          grid = new GridView(document.getElementById("s1-grid"), { size: 640 });
          grid.moveRobot(0, 0, true);
          noteEl = document.getElementById("s1-note");
          scheduleBeat1Highlights();
        },
        step() {
          if (beat === 0) {
            beat = 1;
            scheduler.clearAll();
            grid.setFocusCells([]);
            grid.showSlipDemo(true);
            noteEl.className = "highlight-box amber";
            noteEl.textContent = "Động lực P(s'|s,a): 80% đi đúng hướng, 10% trượt trái, 10% trượt phải.";
          } else {
            onSceneDone();
          }
        },
        currentSegmentKey: () => (beat === 0 ? "s1a" : "s1b"),
        hasNextBeat: () => beat === 0,
        exit() {
          scheduler.clearAll();
        },
      };
    }

    // 2. Agent ngẫu nhiên (25 tập, nhịp chậm rãi)
    function scene2() {
      let grid = null;
      let epIdx = 0;
      let stepIdx = 0;
      let trapTally = 0;
      let goalTally = 0;
      let bannerEl = null;
      let epStatusEl = null;

      function runNextStep() {
        const eps = DATA.episodes.random;
        if (epIdx >= eps.length) {
          epIdx = 0;
          trapTally = 0;
          goalTally = 0;
        }
        const ep = eps[epIdx];
        if (stepIdx === 0) {
          grid.clearFlashes();
          grid.clearPaths();
          grid.moveRobot(ep.states[0], 0, true);
          bannerEl.textContent = `Tập ${epIdx + 1}/${eps.length} · Bẫy: ${trapTally} | Đích: ${goalTally}`;
          epStatusEl.className = "status-pill running";
          epStatusEl.textContent = "Đang di chuyển...";
        }

        if (stepIdx < ep.actions.length) {
          const nextState = ep.states[stepIdx + 1];
          const heading = ep.actions[stepIdx];
          grid.drawPath(ep.states.slice(0, stepIdx + 2), { color: "#6B7280", width: 5, opacity: 0.75 });
          grid.moveRobot(nextState, heading, false);
          stepIdx++;
          scheduler.after(480, runNextStep);
        } else {
          const lastState = ep.states[ep.states.length - 1];
          if (ep.outcome === "trap") {
            trapTally++;
            grid.flashCell(lastState, "trap");
            epStatusEl.className = "status-pill trap";
            epStatusEl.textContent = `Rơi bẫy (${ep.total_reward.toFixed(2)})`;
          } else if (ep.outcome === "goal") {
            goalTally++;
            grid.flashCell(lastState, "goal");
            epStatusEl.className = "status-pill goal";
            epStatusEl.textContent = `Tới đích (+${ep.total_reward.toFixed(2)})`;
          } else {
            epStatusEl.className = "status-pill timeout";
            epStatusEl.textContent = "Hết giờ";
          }
          bannerEl.textContent = `Tập ${epIdx + 1}/${eps.length} · Bẫy: ${trapTally} | Đích: ${goalTally}`;
          epIdx++;
          stepIdx = 0;
          scheduler.after(1400, runNextStep);
        }
      }

      return {
        enter() {
          epIdx = 0;
          stepIdx = 0;
          trapTally = 0;
          goalTally = 0;
          const st = DATA.stats.random;
          stageBody.innerHTML = `
            <div class="split-layout">
              <div class="left-col" id="s2-grid"></div>
              <div class="right-col">
                <div class="episode-banner">
                  <span id="s2-ep-label">Tập 1/${DATA.episodes.random.length} · Bẫy: 0 | Đích: 0</span>
                  <span id="s2-ep-status" class="status-pill running">Đang di chuyển...</span>
                </div>
                <div class="card">
                  <h2 class="scene-heading">2. Khi tác tử hành động ngẫu nhiên</h2>
                  <p class="scene-subtitle">Không có chính sách dẫn đường, robot liên tục trượt vào ô bẫy −10.</p>
                  <div class="metrics-row">
                    <div class="metric-box">
                      <div class="metric-label">Tỉ lệ tới đích (1000 tập)</div>
                      <div class="metric-value green">${fmtPct(st.success_rate)}</div>
                    </div>
                    <div class="metric-box">
                      <div class="metric-label">Tỉ lệ rơi bẫy (1000 tập)</div>
                      <div class="metric-value red">${fmtPct(st.trap_rate)}</div>
                    </div>
                  </div>
                  <div class="highlight-box red">Điểm trung bình: ${st.avg_reward.toFixed(2)} — cần thuật toán tìm chính sách tối ưu.</div>
                </div>
              </div>
            </div>
          `;
          grid = new GridView(document.getElementById("s2-grid"), { size: 640 });
          bannerEl = document.getElementById("s2-ep-label");
          epStatusEl = document.getElementById("s2-ep-status");
          scheduler.after(450, runNextStep);
        },
        step() {
          onSceneDone();
        },
        currentSegmentKey: () => "s2",
        exit() {
          scheduler.clearAll();
        },
      };
    }

    // 3. Value Iteration (48 vòng trải đều theo thời lượng thuyết minh)
    function scene3() {
      let grid = null;
      let k = 0;
      let updateChart = null;
      let iterTextEl = null;
      let convBoxEl = null;
      const maxIter = DATA.vi.iterations;
      const iterDelay = Math.max(650, Math.floor((segDurationMs("s3") - 9000) / maxIter));

      function renderIter(idx) {
        k = Math.max(0, Math.min(maxIter, idx));
        grid.setCellValues(DATA.vi.history[k], true);
        iterTextEl.textContent = `Vòng lặp ${k} / ${maxIter}`;
        if (updateChart) updateChart(k);

        if (k >= maxIter) {
          convBoxEl.className = "highlight-box green";
          convBoxEl.textContent = `Hội tụ sau ${maxIter} vòng (max |ΔV| < 10⁻⁴). V*(1,1) = ${DATA.vi.V_star[0].toFixed(2)}.`;
        } else {
          convBoxEl.className = "highlight-box";
          convBoxEl.textContent = "Giá trị V(s) đang lan truyền ngược từ ô Đích (+10) qua các vòng lặp Bellman.";
        }
      }

      function tick() {
        if (k < maxIter) {
          renderIter(k + 1);
          if (k < maxIter) {
            scheduler.after(iterDelay, tick);
          }
        }
      }

      return {
        enter() {
          k = 0;
          stageBody.innerHTML = `
            <div class="split-layout">
              <div class="left-col" id="s3-grid"></div>
              <div class="right-col">
                <div class="card">
                  <h2 class="scene-heading">3. Thuật toán Value Iteration</h2>
                  <p class="scene-subtitle">Cập nhật trực tiếp Bellman Optimality Backup trên toàn bộ 16 trạng thái.</p>
                  <ul class="bullet-list">
                    <li class="bullet-item"><span class="bullet-dot"></span><span>Ô gần Đích tăng giá trị nhanh; ô sát bẫy bị kéo giảm do 20% trượt.</span></li>
                  </ul>
                  <div id="s3-conv" class="highlight-box"></div>
                </div>
                <div class="card chart-card">
                  <div class="chart-header">
                    <span class="chart-title">Sai số hội tụ max |ΔV| (thang log)</span>
                    <span id="s3-iter" class="chart-iter">Vòng lặp 0 / ${maxIter}</span>
                  </div>
                  <div id="s3-chart"></div>
                </div>
              </div>
            </div>
          `;
          grid = new GridView(document.getElementById("s3-grid"), { size: 640 });
          iterTextEl = document.getElementById("s3-iter");
          convBoxEl = document.getElementById("s3-conv");
          updateChart = buildConvergenceChart(document.getElementById("s3-chart"), DATA.vi.deltas, DATA.params.theta);
          renderIter(0);
          scheduler.after(700, tick);
        },
        step() {
          if (k < maxIter) {
            scheduler.clearAll();
            renderIter(k + 1);
          } else {
            onSceneDone();
          }
        },
        currentSegmentKey: () => "s3",
        exit() {
          scheduler.clearAll();
        },
      };
    }

    // 4. Policy Iteration (mỗi pha dừng đủ lâu để quan sát mũi tên đổi hướng)
    function scene4() {
      let grid = null;
      let stepIdx = 0;
      let phaseEl = null;
      let roundEl = null;
      let noteEl = null;
      const steps = DATA.pi.steps;
      const totalRounds = DATA.pi.iterations;
      const phaseDelay = Math.max(5500, Math.floor((segDurationMs("s4") - 6000) / Math.max(1, steps.length - 1)));

      function renderStep(idx) {
        stepIdx = Math.max(0, Math.min(steps.length - 1, idx));
        const st = steps[stepIdx];
        const isEval = st.phase === "evaluation";

        phaseEl.textContent = isEval ? "Pha 1 · Đánh giá V^π" : "Pha 2 · Cải tiến π";
        phaseEl.className = "status-pill " + (isEval ? "running" : "goal");
        roundEl.textContent = `Vòng ${st.iter + 1} / ${totalRounds}`;

        grid.setCellValues(st.V, false, { smallCorner: true });
        grid.setPolicy(st.policy, { color: "#1D4ED8" });

        const changed = [];
        if (!isEval && stepIdx > 0) {
          const prevPolicy = steps[stepIdx - 1].policy;
          for (let s = 0; s < 16; s++) {
            const [r, c] = stateToRC(s);
            if ((r === 4 && c === 4) || (r === 3 && c === 3) || (r === 2 && c === 3)) continue;
            if (st.policy[s] !== prevPolicy[s]) changed.push(s);
          }
        }
        grid.setChangedCells(changed);

        if (st.is_stable) {
          noteEl.className = "highlight-box green";
          noteEl.textContent = `Chính sách ổn định sau ${totalRounds} vòng! Không còn ô nào đổi hướng.`;
        } else if (isEval) {
          noteEl.className = "highlight-box";
          noteEl.textContent = `Đánh giá xong bảng V^π cho chính sách hiện tại (${st.eval_substeps} bước Bellman tuyến tính).`;
        } else {
          noteEl.className = "highlight-box amber";
          noteEl.textContent = `Đã cập nhật hướng mũi tên tại ${changed.length} ô (tô vàng) theo argmax Q(s, a).`;
        }
      }

      function autoTick() {
        if (stepIdx < steps.length - 1) {
          renderStep(stepIdx + 1);
          if (stepIdx < steps.length - 1) {
            scheduler.after(phaseDelay, autoTick);
          }
        }
      }

      return {
        enter() {
          stepIdx = 0;
          stageBody.innerHTML = `
            <div class="split-layout">
              <div class="left-col" id="s4-grid"></div>
              <div class="right-col">
                <div class="episode-banner">
                  <span id="s4-round">Vòng 1 / ${totalRounds}</span>
                  <span id="s4-phase" class="status-pill running">Pha 1 · Đánh giá V^π</span>
                </div>
                <div class="card">
                  <h2 class="scene-heading">4. Thuật toán Policy Iteration</h2>
                  <p class="scene-subtitle">Luân phiên Đánh giá chính sách V^π và Cải tiến tham lam π.</p>
                  <ul class="bullet-list">
                    <li class="bullet-item"><span class="bullet-dot"></span><span><strong>Pha 1:</strong> Tính giá trị kỳ vọng V^π nếu giữ nguyên hướng đi.</span></li>
                    <li class="bullet-item"><span class="bullet-dot"></span><span><strong>Pha 2:</strong> Lật mũi tên (tô vàng) sang hành động tốt hơn.</span></li>
                    <li class="bullet-item"><span class="bullet-dot"></span><span>Dừng ngay khi chính sách không còn thay đổi.</span></li>
                  </ul>
                  <div id="s4-note" class="highlight-box"></div>
                </div>
              </div>
            </div>
          `;
          grid = new GridView(document.getElementById("s4-grid"), { size: 640 });
          phaseEl = document.getElementById("s4-phase");
          roundEl = document.getElementById("s4-round");
          noteEl = document.getElementById("s4-note");
          renderStep(0);
          scheduler.after(phaseDelay, autoTick);
        },
        step() {
          if (stepIdx < steps.length - 1) {
            scheduler.clearAll();
            renderStep(stepIdx + 1);
          } else {
            onSceneDone();
          }
        },
        currentSegmentKey: () => "s4",
        exit() {
          scheduler.clearAll();
        },
      };
    }

    // 5. Chính sách tối ưu pi* (25 tập, nhịp 620ms/bước)
    function scene5() {
      let grid = null;
      let epIdx = 0;
      let stepIdx = 0;
      let epLabelEl = null;
      let epStatusEl = null;

      function runNextStep() {
        const eps = DATA.episodes.optimal;
        if (epIdx >= eps.length) epIdx = 0;
        const ep = eps[epIdx];

        if (stepIdx === 0) {
          grid.clearFlashes();
          grid.clearPaths();
          grid.moveRobot(ep.states[0], 0, true);
          epLabelEl.textContent = `Tập ${epIdx + 1}/${eps.length} theo π*`;
          epStatusEl.className = "status-pill running";
          epStatusEl.textContent = "Đang di chuyển...";
        }

        if (stepIdx < ep.actions.length) {
          const nextState = ep.states[stepIdx + 1];
          const heading = ep.actions[stepIdx];
          grid.drawPath(ep.states.slice(0, stepIdx + 2), { color: "#16A34A", width: 7, opacity: 0.95, halo: true });
          grid.moveRobot(nextState, heading, false);
          stepIdx++;
          scheduler.after(620, runNextStep);
        } else {
          const lastState = ep.states[ep.states.length - 1];
          grid.flashCell(lastState, ep.outcome === "goal" ? "goal" : "trap");
          epStatusEl.className = "status-pill " + (ep.outcome === "goal" ? "goal" : "trap");
          epStatusEl.textContent = ep.outcome === "goal"
            ? `Tới đích (+${ep.total_reward.toFixed(2)})`
            : `Trượt bẫy (${ep.total_reward.toFixed(2)})`;
          epIdx++;
          stepIdx = 0;
          scheduler.after(1900, runNextStep);
        }
      }

      return {
        enter() {
          epIdx = 0;
          stepIdx = 0;
          const st = DATA.stats.optimal;
          stageBody.innerHTML = `
            <div class="split-layout">
              <div class="left-col" id="s5-grid"></div>
              <div class="right-col">
                <div class="episode-banner">
                  <span id="s5-ep-label">Tập 1/${DATA.episodes.optimal.length} theo π*</span>
                  <span id="s5-ep-status" class="status-pill running">Đang di chuyển...</span>
                </div>
                <div class="card">
                  <h2 class="scene-heading">5. Chính sách tối ưu π*</h2>
                  <p class="scene-subtitle">Robot tự động đi lên dọc Cột 1 rồi sang phải theo Hàng 4, né xa hai ô bẫy.</p>
                  <div class="metrics-row three">
                    <div class="metric-box">
                      <div class="metric-label">V*(1,1)</div>
                      <div class="metric-value blue">${DATA.vi.V_star[0].toFixed(2)}</div>
                    </div>
                    <div class="metric-box">
                      <div class="metric-label">Thành công</div>
                      <div class="metric-value green">${fmtPct(st.success_rate)}</div>
                    </div>
                    <div class="metric-box">
                      <div class="metric-label">Rơi bẫy</div>
                      <div class="metric-value red">${fmtPct(st.trap_rate)}</div>
                    </div>
                  </div>
                  <div class="highlight-box green">Không cần lập trình quy tắc né bẫy: toán Bellman tự cân bằng rủi ro trượt 20%.</div>
                </div>
              </div>
            </div>
          `;
          grid = new GridView(document.getElementById("s5-grid"), { size: 640 });
          grid.setPolicy(DATA.vi.pi_star, { color: "#15803D", opacity: 0.72 });
          epLabelEl = document.getElementById("s5-ep-label");
          epStatusEl = document.getElementById("s5-ep-status");
          scheduler.after(550, runNextStep);
        },
        step() {
          onSceneDone();
        },
        currentSegmentKey: () => "s5",
        exit() {
          scheduler.clearAll();
        },
      };
    }

    // 6. So sánh π* vs đường tắt sát bẫy (25 lượt đua song song, nhịp 640ms/bước)
    function scene6() {
      let gOpt = null;
      let gRisky = null;
      let epIdx = 1;
      let racesDone = 0;
      let stepIdx = 0;
      let statusOptEl = null;
      let statusRiskyEl = null;

      const OPT_THEORY = [0, 4, 8, 12, 13, 14, 15];
      const RISKY_THEORY = [0, 1, 2, 3, 7, 11, 15];

      function runRaceStep() {
        const epsOpt = DATA.episodes.optimal;
        const epsRisky = DATA.episodes.risky;
        const idx = epIdx % epsOpt.length;

        const epO = epsOpt[idx];
        const epR = epsRisky[idx];

        if (stepIdx === 0) {
          gOpt.clearFlashes();
          gRisky.clearFlashes();
          gOpt.drawPath(OPT_THEORY, { color: "#16A34A", width: 5, opacity: 0.35, layerId: "theory" });
          gRisky.drawPath(RISKY_THEORY, { color: "#DC2626", dashed: true, width: 5, opacity: 0.4, layerId: "theory" });
          gOpt.drawPath([], { layerId: "live" });
          gRisky.drawPath([], { layerId: "live" });
          gOpt.moveRobot(epO.states[0], 0, true);
          gRisky.moveRobot(epR.states[0], 3, true);
          statusOptEl.className = "status-pill running";
          statusOptEl.textContent = `Lượt ${racesDone + 1}: Đang chạy`;
          statusRiskyEl.className = "status-pill running";
          statusRiskyEl.textContent = `Lượt ${racesDone + 1}: Đang chạy`;
        }

        const optDone = stepIdx >= epO.actions.length;
        const riskyDone = stepIdx >= epR.actions.length;

        if (!optDone) {
          gOpt.drawPath(epO.states.slice(0, stepIdx + 2), { color: "#16A34A", width: 6, opacity: 0.95, layerId: "live", halo: true });
          gOpt.moveRobot(epO.states[stepIdx + 1], epO.actions[stepIdx], false);
          if (stepIdx + 1 >= epO.actions.length) {
            const last = epO.states[epO.states.length - 1];
            gOpt.flashCell(last, epO.outcome === "goal" ? "goal" : "trap");
            statusOptEl.className = "status-pill " + (epO.outcome === "goal" ? "goal" : "trap");
            statusOptEl.textContent = epO.outcome === "goal" ? `Đích (+${epO.total_reward.toFixed(1)})` : "Rơi bẫy";
          }
        }

        if (!riskyDone) {
          gRisky.drawPath(epR.states.slice(0, stepIdx + 2), { color: "#DC2626", width: 6, opacity: 0.95, layerId: "live", halo: true });
          gRisky.moveRobot(epR.states[stepIdx + 1], epR.actions[stepIdx], false);
          if (stepIdx + 1 >= epR.actions.length) {
            const last = epR.states[epR.states.length - 1];
            if (epR.outcome !== "timeout") gRisky.flashCell(last, epR.outcome === "goal" ? "goal" : "trap");
            statusRiskyEl.className = "status-pill " + (epR.outcome === "goal" ? "goal" : epR.outcome === "trap" ? "trap" : "timeout");
            statusRiskyEl.textContent = epR.outcome === "goal"
              ? `Đích (+${epR.total_reward.toFixed(1)})`
              : epR.outcome === "trap"
                ? `Rơi bẫy (${epR.total_reward.toFixed(1)})`
                : "Hết giờ";
          }
        }

        if (!optDone || !riskyDone) {
          stepIdx++;
          scheduler.after(640, runRaceStep);
        } else {
          epIdx++;
          racesDone++;
          stepIdx = 0;
          scheduler.after(2200, runRaceStep);
        }
      }

      return {
        enter() {
          epIdx = 1;
          racesDone = 0;
          stepIdx = 0;
          const stOpt = DATA.stats.optimal;
          const stRisky = DATA.stats.risky;

          stageBody.innerHTML = `
            <div class="compare-layout">
              <div class="compare-pair">
                <div class="compare-card">
                  <div class="compare-card-header">
                    <span class="compare-card-title opt">Chính sách tối ưu π* (Đi vòng an toàn)</span>
                    <span id="s6-st-opt" class="status-pill running">Đang chạy</span>
                  </div>
                  <div id="s6-grid-opt"></div>
                  <div class="compare-stats">
                    <div class="compare-stat-item">
                      <div class="compare-stat-label">V(Start)</div>
                      <div class="compare-stat-val" style="color:var(--start)">${DATA.vi.V_star[0].toFixed(2)}</div>
                    </div>
                    <div class="compare-stat-item">
                      <div class="compare-stat-label">Thành công</div>
                      <div class="compare-stat-val" style="color:var(--opt)">${fmtPct(stOpt.success_rate)}</div>
                    </div>
                    <div class="compare-stat-item">
                      <div class="compare-stat-label">Rơi bẫy</div>
                      <div class="compare-stat-val" style="color:var(--risky)">${fmtPct(stOpt.trap_rate)}</div>
                    </div>
                  </div>
                </div>

                <div class="compare-card">
                  <div class="compare-card-header">
                    <span class="compare-card-title risky">Đường tắt sát bẫy (Mạo hiểm)</span>
                    <span id="s6-st-risky" class="status-pill running">Đang chạy</span>
                  </div>
                  <div id="s6-grid-risky"></div>
                  <div class="compare-stats">
                    <div class="compare-stat-item">
                      <div class="compare-stat-label">V(Start)</div>
                      <div class="compare-stat-val" style="color:var(--start)">${DATA.risky.V[0].toFixed(2)}</div>
                    </div>
                    <div class="compare-stat-item">
                      <div class="compare-stat-label">Thành công</div>
                      <div class="compare-stat-val" style="color:var(--opt)">${fmtPct(stRisky.success_rate)}</div>
                    </div>
                    <div class="compare-stat-item">
                      <div class="compare-stat-label">Rơi bẫy</div>
                      <div class="compare-stat-val" style="color:var(--risky)">${fmtPct(stRisky.trap_rate)}</div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="conclusion-banner">
                Cùng 6 bước — nhưng đường sát bẫy rủi ro cao hơn. Bellman tự cân bằng chi phí và an toàn.
              </div>
            </div>
          `;

          gOpt = new GridView(document.getElementById("s6-grid-opt"), { size: 440, compact: true });
          gRisky = new GridView(document.getElementById("s6-grid-risky"), { size: 440, compact: true });
          gOpt.setPolicy(DATA.vi.pi_star, { color: "#16A34A", arrowScale: 0.9, opacity: 0.65 });
          gRisky.setPolicy(DATA.risky.policy, { color: "#DC2626", arrowScale: 0.9, opacity: 0.65 });
          statusOptEl = document.getElementById("s6-st-opt");
          statusRiskyEl = document.getElementById("s6-st-risky");

          scheduler.after(600, runRaceStep);
        },
        step() {
          goToScene(0);
        },
        currentSegmentKey: () => "s6",
        exit() {
          scheduler.clearAll();
        },
      };
    }

    return [scene1(), scene2(), scene3(), scene4(), scene5(), scene6()];
  }

  // ===================== ĐIỀU PHỐI CHÍNH & TRÌNH PHÁT GIỌNG ĐỌC =====================
  const stage = document.getElementById("stage");
  const stageBody = document.getElementById("stage-body");
  const counterEl = document.getElementById("scene-counter");
  const dotsEl = document.getElementById("scene-dots");
  const hintBar = document.getElementById("hint-bar");
  const modeBadge = document.getElementById("mode-badge");

  const scheduler = new Scheduler();
  const voicePlayer = new Audio();
  let voiceEnabled = Boolean(AUDIO_META);
  let currentIdx = 0;
  let autoPlay = false;
  let autoTimer = null;
  let hintsVisible = true;

  function fitStage() {
    const scale = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
    stage.style.transform = `translate(-50%, -50%) scale(${scale})`;
  }
  window.addEventListener("resize", fitStage);
  fitStage();

  const scenes = createScenes(
    stageBody,
    scheduler,
    () => {
      if (currentIdx < scenes.length - 1) {
        goToScene(currentIdx + 1);
      }
    },
    (idx) => goToScene(idx)
  );

  const dots = scenes.map((_, idx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "scene-dot";
    btn.title = `Cảnh ${idx + 1}`;
    btn.addEventListener("click", () => {
      stopAutoPlay();
      goToScene(idx);
    });
    dotsEl.appendChild(btn);
    return btn;
  });

  function stopVoice() {
    voicePlayer.onended = null;
    voicePlayer.onerror = null;
    try {
      voicePlayer.pause();
      voicePlayer.currentTime = 0;
    } catch (_) {}
  }

  function clearAutoTimer() {
    if (autoTimer) {
      clearTimeout(autoTimer);
      autoTimer = null;
    }
  }

  function updateHeader() {
    counterEl.textContent = `Cảnh ${currentIdx + 1}/6`;
    dots.forEach((d, i) => d.classList.toggle("active", i === currentIdx));

    if (!hintsVisible) {
      modeBadge.classList.add("hidden");
      return;
    }
    const voiceTag = voiceEnabled ? " · Có giọng đọc" : " · Tắt tiếng (M)";
    if (scheduler.paused) {
      modeBadge.textContent = "Đang tạm dừng (P)";
      modeBadge.className = "mode-badge paused";
    } else if (autoPlay) {
      modeBadge.textContent = "Tự động phát (A)" + voiceTag;
      modeBadge.className = "mode-badge";
    } else if (!voiceEnabled) {
      modeBadge.textContent = "Đã tắt giọng đọc (M)";
      modeBadge.className = "mode-badge";
    } else {
      modeBadge.className = "mode-badge hidden";
    }
  }

  function advanceAutoStep() {
    if (!autoPlay || scheduler.paused) return;
    const sc = scenes[currentIdx];
    if (sc.hasNextBeat && sc.hasNextBeat()) {
      sc.step();
      playSegmentAudio(sc.currentSegmentKey());
    } else if (currentIdx < scenes.length - 1) {
      goToScene(currentIdx + 1);
    } else {
      stopAutoPlay();
    }
  }

  function playSegmentAudio(key) {
    clearAutoTimer();
    stopVoice();
    if (!autoPlay || scheduler.paused) return;

    const durMs = segDurationMs(key);
    const src = segSrc(key);

    if (voiceEnabled && src) {
      voicePlayer.src = src;
      voicePlayer.currentTime = 0;
      voicePlayer.onended = () => {
        voicePlayer.onended = null;
        if (!autoPlay || scheduler.paused) return;
        autoTimer = setTimeout(advanceAutoStep, GAP_MS);
      };
      voicePlayer.onerror = () => {
        voicePlayer.onerror = null;
        if (!autoPlay || scheduler.paused) return;
        autoTimer = setTimeout(advanceAutoStep, durMs + GAP_MS);
      };
      const playPromise = voicePlayer.play();
      if (playPromise && typeof playPromise.catch === "function") {
        playPromise.catch(() => {
          voicePlayer.onended = null;
          if (!autoPlay || scheduler.paused) return;
          autoTimer = setTimeout(advanceAutoStep, durMs + GAP_MS);
        });
      }
    } else {
      autoTimer = setTimeout(advanceAutoStep, durMs + GAP_MS);
    }
  }

  function stopAutoPlay() {
    autoPlay = false;
    clearAutoTimer();
    stopVoice();
    updateHeader();
  }

  function startAutoPlay() {
    autoPlay = true;
    scheduler.resume();
    goToScene(0);
  }

  function goToScene(idx) {
    const target = Math.max(0, Math.min(scenes.length - 1, idx));
    if (scenes[currentIdx]) {
      scenes[currentIdx].exit();
    }
    scheduler.clearAll();
    clearAutoTimer();
    stopVoice();
    currentIdx = target;
    scenes[currentIdx].enter();
    updateHeader();
    if (autoPlay) {
      playSegmentAudio(scenes[currentIdx].currentSegmentKey());
    }
  }

  document.addEventListener("keydown", (e) => {
    if (e.key >= "1" && e.key <= "6") {
      stopAutoPlay();
      goToScene(Number(e.key) - 1);
      return;
    }

    switch (e.key) {
      case " ":
      case "ArrowRight":
        e.preventDefault();
        stopAutoPlay();
        scenes[currentIdx].step();
        break;
      case "ArrowLeft":
        e.preventDefault();
        stopAutoPlay();
        if (currentIdx > 0) goToScene(currentIdx - 1);
        break;
      case "p":
      case "P":
        if (scheduler.paused) {
          scheduler.resume();
          if (autoPlay) {
            if (voiceEnabled && voicePlayer.src && voicePlayer.paused && !voicePlayer.ended) {
              voicePlayer.play().catch(() => {});
            } else {
              playSegmentAudio(scenes[currentIdx].currentSegmentKey());
            }
          }
        } else {
          scheduler.pause();
          clearAutoTimer();
          if (!voicePlayer.paused) {
            try { voicePlayer.pause(); } catch (_) {}
          }
        }
        updateHeader();
        break;
      case "r":
      case "R":
        goToScene(currentIdx);
        break;
      case "a":
      case "A":
        if (autoPlay) stopAutoPlay();
        else startAutoPlay();
        break;
      case "m":
      case "M":
        voiceEnabled = !voiceEnabled;
        if (!voiceEnabled) {
          stopVoice();
          if (autoPlay && !scheduler.paused) {
            playSegmentAudio(scenes[currentIdx].currentSegmentKey());
          }
        } else if (autoPlay && !scheduler.paused) {
          playSegmentAudio(scenes[currentIdx].currentSegmentKey());
        }
        updateHeader();
        break;
      case "h":
      case "H":
        hintsVisible = !hintsVisible;
        hintBar.classList.toggle("hidden", !hintsVisible);
        updateHeader();
        break;
      case "f":
      case "F":
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen?.().catch(() => {});
        } else {
          document.exitFullscreen?.().catch(() => {});
        }
        break;
    }
  });

  goToScene(0);
})();
