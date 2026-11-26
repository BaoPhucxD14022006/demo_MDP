(function () {
  "use strict";

  const DATA = window.MDP_DATA;
  if (!DATA) {
    document.body.innerHTML = "<p style='padding:40px;font-size:24px'>Không tìm thấy dữ liệu web/data.js. Hãy chạy <code>python scripts/export_web_data.py</code>.</p>";
    return;
  }

  const AUDIO_META = window.MDP_AUDIO || null;
  const GAP_MS = (AUDIO_META && AUDIO_META.gapMs) || 1200;
  const FALLBACK_DURS = {
    s1a: 34460,
    s1b: 22490,
    s2: 40990,
    s3: 62130,
    s4: 39230,
    s5: 44110,
    s6: 119010,
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
  const FOCUS_CLASSES = ["focus-blue", "focus-green", "focus-red", "focus-amber"];

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

  function setCue(activeIds, allIds) {
    const activeSet = new Set(Array.isArray(activeIds) ? activeIds : (activeIds ? [activeIds] : []));
    for (const id of allIds) {
      const el = document.getElementById(id);
      if (el) el.classList.toggle("cue-active", activeSet.has(id));
    }
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

    setFocusCells(indices, tone = "blue") {
      const cls = `focus-${tone}`;
      const set = new Set(indices);
      for (let s = 0; s < 16; s++) {
        const el = this.cells[s].el;
        el.classList.remove(...FOCUS_CLASSES);
        if (set.has(s)) {
          el.classList.add(cls);
        }
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
      if (!states || states.length < 2) {
        this.cellsGrid.classList.toggle("has-path", this.pathLayer.children.length > 0);
        return;
      }

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
      this.cellsGrid.classList.add("has-path");
    }

    clearPaths() {
      this.pathLayer.innerHTML = "";
      this.cellsGrid.classList.remove("has-path");
    }

    moveRobot(s, heading = 0, instant = false) {
      const { x, y } = this.cellCenter(s);
      this.cellsGrid.classList.toggle("robot-at-start", s === 0);
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
      this.cellsGrid.classList.remove("robot-at-start");
    }

    flashCell(s, kind) {
      const el = this.cells[s].el;
      const cls = kind === "goal" ? "flash-goal" : "flash-trap";
      el.classList.add(cls);
      return cls;
    }

    clearFlashes() {
      for (const c of this.cells) {
        c.el.classList.remove("flash-trap", "flash-goal", "changed", ...FOCUS_CLASSES);
      }
    }

    showActionCross(show) {
      this.slipLayer.innerHTML = "";
      if (!show) return;
      // Ô trống (2,2) -> s = (2-1)*4 + (2-1) = 5
      const { x, y } = this.cellCenter(5);
      const col = "#2563EB";
      this._drawSvgArrow(this.slipLayer, x, y - 10, x, y - 56, col, 4, 11);
      this._drawSvgArrow(this.slipLayer, x, y + 10, x, y + 56, col, 4, 11);
      this._drawSvgArrow(this.slipLayer, x - 10, y, x - 56, y, col, 4, 11);
      this._drawSvgArrow(this.slipLayer, x + 10, y, x + 56, y, col, 4, 11);
      const lbl = svgEl("text", {
        x, y: y + 4, "text-anchor": "middle",
        fill: "#1E40AF", "font-size": 16, "font-weight": 800,
      });
      lbl.textContent = "A";
      this.slipLayer.appendChild(lbl);
    }

    showSlipDemo(mode) {
      this.slipLayer.innerHTML = "";
      if (!mode || mode === "none") return;
      const { x, y } = this.cellCenter(0);
      const sc = this.compact ? 0.68 : 1;

      this._drawSvgArrow(this.slipLayer, x, y - 28 * sc, x, y - 125 * sc, "#16A34A", 7 * sc, 16 * sc);
      const tMain = svgEl("text", {
        x: x + 16 * sc, y: y - 92 * sc,
        fill: "#15803D", "font-size": Math.round(24 * sc), "font-weight": 800,
      });
      tMain.textContent = "80% thẳng";
      this.slipLayer.appendChild(tMain);

      if (mode === "all") {
        this._drawSvgArrow(this.slipLayer, x + 28 * sc, y, x + 115 * sc, y, "#F59E0B", 4 * sc, 12 * sc);
        const tRight = svgEl("text", {
          x: x + 56 * sc, y: y - 14 * sc,
          fill: "#B45309", "font-size": Math.round(20 * sc), "font-weight": 700,
        });
        tRight.textContent = "10% trượt";
        this.slipLayer.appendChild(tRight);

        this._drawSvgArrow(this.slipLayer, x - 24 * sc, y, x - (this.compact ? 52 : 72), y, "#F59E0B", 4 * sc, 11 * sc);
        const tLeft = svgEl("text", {
          x: x - (this.compact ? 50 : 74), y: y - 14 * sc,
          fill: "#B45309", "font-size": Math.round(19 * sc), "font-weight": 700,
        });
        tLeft.textContent = "10%";
        this.slipLayer.appendChild(tLeft);
      }
    }

    clear() {
      this.clearPaths();
      this.arrowLayer.innerHTML = "";
      this.cellsGrid.classList.remove("has-arrows", "robot-at-start", "has-path");
      this.slipLayer.innerHTML = "";
      this.clearFlashes();
      this.setCellValues(null, false);
      this._renderStaticBadges();
      this.hideRobot();
    }
  }

  // ===================== BỘ LẬP LỊCH THỐNG NHẤT =====================
  class Scheduler {
    constructor(initialSpeed = 1) {
      this.timers = new Set();
      this.paused = false;
      this.speed = initialSpeed > 0 ? initialSpeed : 1;
    }

    _arm(item) {
      item.start = performance.now();
      const delay = Math.max(0, item.remaining / this.speed);
      item.id = setTimeout(() => {
        item.id = null;
        item.done = true;
        this.timers.delete(item);
        item.fn();
      }, delay);
    }

    after(ms, fn) {
      const item = { id: null, fn, remaining: ms, start: performance.now(), done: false };
      this.timers.add(item);
      if (!this.paused) {
        this._arm(item);
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
          const elapsedBase = (now - item.start) * this.speed;
          item.remaining = Math.max(0, item.remaining - elapsedBase);
        }
      }
    }

    resume() {
      if (!this.paused) return;
      this.paused = false;
      for (const item of [...this.timers]) {
        if (!item.done && item.id === null) {
          this._arm(item);
        }
      }
    }

    setSpeed(newSpeed) {
      if (newSpeed <= 0 || newSpeed === this.speed) return;
      const now = performance.now();
      const oldSpeed = this.speed;
      this.speed = newSpeed;
      if (!this.paused) {
        for (const item of [...this.timers]) {
          if (!item.done && item.id !== null) {
            clearTimeout(item.id);
            item.id = null;
            const elapsedBase = (now - item.start) * oldSpeed;
            item.remaining = Math.max(0, item.remaining - elapsedBase);
            this._arm(item);
          }
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
    const tLbl = svgEl("text", { x: pad.l + 8, y: yTheta - 8, "text-anchor": "start", fill: "#DC2626", "font-size": 14, "font-weight": 700 });
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

  // ===================== 6 CẢNH DEMO ĐỒNG BỘ GIỌNG ĐỌC =====================
  function createScenes(stageBody, scheduler, onSceneDone, goToScene, isAutoPlay) {
    // 1. Môi trường MDP (Beat 0 = s1a 34.5s, Beat 1 = s1b 22.5s)
    function scene1() {
      let grid = null;
      let beat = 0;
      let noteEl = null;
      const S1_BULLETS = ["s1-b1", "s1-b2", "s1-b3", "s1-b4"];

      function scheduleBeat1Synced() {
        if (!isAutoPlay()) return;
        noteEl.textContent = "Giới thiệu mô hình MDP trên lưới 4×4.";

        // 6.7s: Câu 2 — S (16 ô từ (1,1) đến (4,4)) & A (4 hành động)
        scheduler.after(6700, () => {
          if (beat !== 0) return;
          setCue("s1-b1", S1_BULLETS);
          grid.setFocusCells([0], "blue");
        });
        scheduler.after(10800, () => {
          if (beat !== 0) return;
          grid.setFocusCells([15], "green");
        });
        scheduler.after(12600, () => {
          if (beat !== 0) return;
          setCue("s1-b2", S1_BULLETS);
          grid.setFocusCells([]);
          grid.showActionCross(true);
        });

        // 15.8s: Câu 3 — Phần thưởng R: Đích (4,4) +10 & Bẫy (3,3),(3,2) -10
        scheduler.after(15800, () => {
          if (beat !== 0) return;
          grid.showActionCross(false);
          setCue("s1-b3", S1_BULLETS);
          grid.setFocusCells([15], "green");
          noteEl.className = "highlight-box green";
          noteEl.textContent = "Ô Đích (4,4) mang lại phần thưởng +10.";
        });
        scheduler.after(18300, () => {
          if (beat !== 0) return;
          grid.setFocusCells([10, 6], "red");
          noteEl.className = "highlight-box red";
          noteEl.textContent = "Hai ô Bẫy (3,3) và (3,2) phạt −10 và kết thúc lượt đi.";
        });

        // 23.1s: Câu 4 — Chi phí bước −0.04, va tường −0.2
        scheduler.after(23100, () => {
          if (beat !== 0) return;
          grid.setFocusCells([4, 0], "amber");
          noteEl.className = "highlight-box amber";
          noteEl.textContent = "Mỗi bước đi: −0.04 · Va tường biên: đứng yên & −0.2.";
        });

        // 29.7s: Câu 5 — γ = 0.99
        scheduler.after(29700, () => {
          if (beat !== 0) return;
          grid.setFocusCells([]);
          setCue("s1-b4", S1_BULLETS);
          noteEl.className = "highlight-box";
          noteEl.textContent = "Hệ số chiết khấu γ = 0.99: ưu tiên phần thưởng dài hạn.";
        });
      }

      function scheduleBeat2Synced() {
        setCue([], S1_BULLETS);
        if (!isAutoPlay()) {
          grid.setFocusCells([0], "blue");
          grid.showSlipDemo("all");
          noteEl.className = "highlight-box amber";
          noteEl.textContent = "Động lực P(s'|s,a): 80% đi đúng hướng, 10% trượt trái, 10% trượt phải.";
          return;
        }

        // 0.0s: Câu 1 — giới thiệu yếu tố ngẫu nhiên
        grid.setFocusCells([0], "blue");
        grid.showSlipDemo("none");
        noteEl.className = "highlight-box";
        noteEl.textContent = "Động lực chuyển trạng thái ngẫu nhiên P(s'|s,a)...";

        // 6.0s: Câu 2 — 80% đi đúng hướng
        scheduler.after(6000, () => {
          if (beat !== 1) return;
          grid.showSlipDemo("main");
          noteEl.className = "highlight-box green";
          noteEl.textContent = "80% xác suất robot đi đúng hướng đã chọn.";
        });

        // 12.0s: Câu 3 — 10% trượt trái, 10% trượt phải
        scheduler.after(12000, () => {
          if (beat !== 1) return;
          grid.showSlipDemo("all");
          noteEl.className = "highlight-box amber";
          noteEl.textContent = "20% còn lại: 10% trượt vuông góc sang trái, 10% trượt sang phải.";
        });

        // 17.8s: Câu 4 — cảnh báo đi sát mép bẫy
        scheduler.after(17800, () => {
          if (beat !== 1) return;
          grid.setFocusCells([10, 6], "red");
          noteEl.className = "highlight-box red";
          noteEl.textContent = "Độ trượt 20% khiến việc đi sát mép bẫy cực kỳ nguy hiểm.";
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
                    <li id="s1-b1" class="bullet-item"><span class="bullet-dot"></span><span><strong>S (Trạng thái):</strong> 16 ô lưới từ (1,1) đến (4,4).</span></li>
                    <li id="s1-b2" class="bullet-item"><span class="bullet-dot"></span><span><strong>A (Hành động):</strong> { Lên, Xuống, Trái, Phải }.</span></li>
                    <li id="s1-b3" class="bullet-item"><span class="bullet-dot"></span><span><strong>R (Phần thưởng):</strong> Đích +10, Bẫy −10, mỗi bước −0.04 (va tường −0.2).</span></li>
                    <li id="s1-b4" class="bullet-item"><span class="bullet-dot"></span><span><strong>γ = 0.99:</strong> Ưu tiên phần thưởng dài hạn.</span></li>
                  </ul>
                  <div id="s1-note" class="highlight-box">Nhấn Space để xem động lực ngẫu nhiên 80 / 10 / 10.</div>
                </div>
              </div>
            </div>
          `;
          grid = new GridView(document.getElementById("s1-grid"), { size: 640 });
          grid.moveRobot(0, 0, true);
          noteEl = document.getElementById("s1-note");
          scheduleBeat1Synced();
        },
        step() {
          if (beat === 0) {
            beat = 1;
            scheduler.clearAll();
            grid.showActionCross(false);
            grid.setFocusCells([]);
            scheduleBeat2Synced();
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

    // 2. Agent ngẫu nhiên (s2: 40.51s)
    function scene2() {
      let grid = null;
      let epIdx = 0;
      let stepIdx = 0;
      let trapTally = 0;
      let goalTally = 0;
      let bannerEl = null;
      let epStatusEl = null;
      const S2_METRICS = ["s2-m-goal", "s2-m-trap", "s2-m-timeout"];

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
            epStatusEl.textContent = "Timeout";
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
                  <p class="scene-subtitle">Thống kê 1.000 tập (tối đa 50 bước/tập): robot thường xuyên trượt vào ô bẫy −10.</p>
                  <div class="metrics-row three">
                    <div id="s2-m-goal" class="metric-box">
                      <div class="metric-label">Tới đích</div>
                      <div class="metric-value green">${fmtPct(st.success_rate)}</div>
                    </div>
                    <div id="s2-m-trap" class="metric-box">
                      <div class="metric-label">Rơi bẫy</div>
                      <div class="metric-value red">${fmtPct(st.trap_rate)}</div>
                    </div>
                    <div id="s2-m-timeout" class="metric-box">
                      <div class="metric-label">Timeout</div>
                      <div class="metric-value muted">${fmtPct(st.timeout_rate)}</div>
                    </div>
                  </div>
                  <div class="highlight-box red">Tổng 3 kết cục = 100.0% · Điểm trung bình: ${st.avg_reward.toFixed(2)} — cần thuật toán tối ưu.</div>
                </div>
              </div>
            </div>
          `;
          grid = new GridView(document.getElementById("s2-grid"), { size: 640 });
          bannerEl = document.getElementById("s2-ep-label");
          epStatusEl = document.getElementById("s2-ep-status");
          scheduler.after(450, runNextStep);

          if (isAutoPlay()) {
            scheduler.after(20400, () => setCue("s2-m-goal", S2_METRICS));
            scheduler.after(27200, () => setCue("s2-m-trap", S2_METRICS));
            scheduler.after(29800, () => setCue("s2-m-timeout", S2_METRICS));
            scheduler.after(35800, () => setCue([], S2_METRICS));
          }
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

    // 3. Value Iteration & Trích xuất chính sách (s3: 62.13s)
    function scene3() {
      let grid = null;
      let k = 0;
      let extracted = false;
      let updateChart = null;
      let iterTextEl = null;
      let convBoxEl = null;
      const maxIter = DATA.vi.iterations; // 48
      const S3_BULLETS = ["s3-b1", "s3-b2"];

      function renderIter(idx) {
        k = Math.max(0, Math.min(maxIter, idx));
        grid.setCellValues(DATA.vi.history[k], true);
        iterTextEl.textContent = `Vòng lặp ${k} / ${maxIter}`;
        if (updateChart) updateChart(k);

        if (k === 0) {
          convBoxEl.className = "highlight-box";
          convBoxEl.textContent = "Khởi tạo V₀(s) = 0 trên tất cả 16 trạng thái trước khi lặp Bellman.";
        } else if (k >= maxIter) {
          convBoxEl.className = "highlight-box green";
          convBoxEl.textContent = `Hội tụ sau ${maxIter} vòng (max |ΔV| < 10⁻⁴). V*(1,1) = ${DATA.vi.V_star[0].toFixed(2)}.`;
        } else {
          convBoxEl.className = "highlight-box";
          convBoxEl.textContent = "Giá trị V(s) đang lan truyền ngược từ ô Đích (+10) qua các vòng lặp Bellman.";
        }
      }

      function showExtractedPolicy() {
        if (extracted) return;
        extracted = true;
        if (k < maxIter) renderIter(maxIter);
        grid.setCellValues(DATA.vi.V_star, true, { smallCorner: true });
        grid.setPolicy(DATA.vi.pi_star, { color: "#FFFFFF", arrowScale: 0.92, opacity: 0.95 });
        convBoxEl.className = "highlight-box green";
        convBoxEl.textContent = "Đã trích xuất π*(s) = argmax Q*(s,a) từ V*! Ví dụ tại (1,1): đi Lên (6.96) > sang Phải (6.65).";
      }

      const stepMs = 670; // 48 * 670ms = 32.16s -> bắt đầu ở 6.8s, hội tụ đúng 38.96s
      function tick() {
        if (k < maxIter) {
          renderIter(k + 1);
          if (k < maxIter) {
            scheduler.after(stepMs, tick);
          } else if (!isAutoPlay()) {
            scheduler.after(1200, showExtractedPolicy);
          }
        }
      }

      return {
        enter() {
          k = 0;
          extracted = false;
          stageBody.innerHTML = `
            <div class="split-layout">
              <div class="left-col" id="s3-grid"></div>
              <div class="right-col">
                <div class="card">
                  <h2 class="scene-heading">3. Thuật toán Value Iteration</h2>
                  <p class="scene-subtitle">Cập nhật trực tiếp Bellman Optimality Backup trên toàn bộ 16 trạng thái.</p>
                  <ul class="bullet-list">
                    <li id="s3-b1" class="bullet-item"><span class="bullet-dot"></span><span><strong>Bước 1 (Tính V*):</strong> Lan truyền giá trị từ Đích; ô sát bẫy giảm do 20% trượt.</span></li>
                    <li id="s3-b2" class="bullet-item"><span class="bullet-dot"></span><span><strong>Bước 2 (Trích xuất π*):</strong> Từ V*, nhìn trước 1 bước chọn hướng argmax Q*(s,a).</span></li>
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

          if (isAutoPlay()) {
            setCue("s3-b1", S3_BULLETS);
            scheduler.after(6800, tick);
            // 19.9s: Câu 4 — ô lân cận đích (3,4) [s=14] & (4,3) [s=11]
            scheduler.after(19900, () => grid.setFocusCells([14, 11], "green"));
            // 26.8s: Câu 5 — ô sát bẫy hàng 1: (3,1) [s=2] & (4,1) [s=3]
            scheduler.after(26800, () => grid.setFocusCells([2, 3], "red"));
            scheduler.after(34000, () => grid.setFocusCells([]));
            // 39.2s: Câu 6 — hội tụ 48 vòng, V*(1,1) = 6.78
            scheduler.after(39200, () => grid.setFocusCells([0], "blue"));
            // 43.7s: Câu 7 — chuyển sang Bước 2: Trích xuất chính sách π* từ V*
            scheduler.after(43700, () => {
              grid.setFocusCells([]);
              setCue("s3-b2", S3_BULLETS);
            });
            scheduler.after(46500, showExtractedPolicy);
            // 55.0s: Câu 8 — ví dụ nhìn trước 1 bước tại (1,1): Lên (1,2)=6.96 vs Phải (2,1)=6.65
            scheduler.after(55000, () => {
              grid.setFocusCells([0, 4], "green");
              grid.cells[1].el.classList.add("focus-amber");
            });
            scheduler.after(61200, () => {
              grid.setFocusCells([]);
              setCue([], S3_BULLETS);
            });
          } else {
            scheduler.after(1200, tick);
          }
        },
        step() {
          if (k < maxIter) {
            scheduler.clearAll();
            grid.setFocusCells([]);
            renderIter(k + 1);
          } else if (!extracted) {
            scheduler.clearAll();
            grid.setFocusCells([]);
            setCue("s3-b2", S3_BULLETS);
            showExtractedPolicy();
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

    // 4. Policy Iteration (s4: 39.23s)
    function scene4() {
      let grid = null;
      let stepIdx = 0;
      let phaseEl = null;
      let roundEl = null;
      let noteEl = null;
      const steps = DATA.pi.steps;
      const totalRounds = DATA.pi.iterations;
      const S4_BULLETS = ["s4-b1", "s4-b2", "s4-b3"];

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

      function autoTickManual() {
        if (stepIdx < steps.length - 1) {
          renderStep(stepIdx + 1);
          if (stepIdx < steps.length - 1) {
            scheduler.after(5500, autoTickManual);
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
                    <li id="s4-b1" class="bullet-item"><span class="bullet-dot"></span><span><strong>Pha 1:</strong> Tính giá trị kỳ vọng V^π nếu giữ nguyên hướng đi.</span></li>
                    <li id="s4-b2" class="bullet-item"><span class="bullet-dot"></span><span><strong>Pha 2:</strong> Lật mũi tên (tô vàng) sang hành động tốt hơn.</span></li>
                    <li id="s4-b3" class="bullet-item"><span class="bullet-dot"></span><span>Dừng ngay khi chính sách không còn thay đổi.</span></li>
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

          if (isAutoPlay()) {
            // 7.1s: Câu 2 — Pha 1 Đánh giá V^π
            scheduler.after(7100, () => setCue("s4-b1", S4_BULLETS));
            // 15.3s: Câu 3 & 4 — Pha 2 Cải tiến π (tô vàng các ô đổi hướng)
            scheduler.after(15300, () => {
              renderStep(1);
              setCue("s4-b2", S4_BULLETS);
            });
            // 25.6s..29.8s: Câu 5 — qua Vòng 2 và ổn định ở Vòng 3
            scheduler.after(25600, () => renderStep(2));
            scheduler.after(27000, () => renderStep(3));
            scheduler.after(28400, () => renderStep(4));
            scheduler.after(29800, () => {
              renderStep(5);
              setCue("s4-b3", S4_BULLETS);
            });
          } else {
            scheduler.after(5500, autoTickManual);
          }
        },
        step() {
          if (stepIdx < steps.length - 1) {
            scheduler.clearAll();
            setCue([], S4_BULLETS);
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

    // 5. Chính sách tối ưu pi* (s5: 44.11s)
    function scene5() {
      let grid = null;
      let orderPos = 0;
      let stepIdx = 0;
      let epLabelEl = null;
      let epStatusEl = null;
      const S5_METRICS = ["s5-m-goal", "s5-m-trap"];
      // Thứ tự phát tuyển chọn khớp lời thoại:
      // opt[7] đi thẳng Cột 1 -> Hàng 4; opt[10] trượt qua (2,1) rồi rẽ trái về (1,1);
      // opt[11] tới đích; opt[13] trượt tại (3,4) rơi xuống bẫy (3,3) đúng lúc đọc 11.5%.
      const OPT_ORDER = [7, 10, 11, 13, 14, 2, 3, 4, 8, 9, 12, 15, 17, 20, 21, 22, 0, 1, 5, 6, 16, 18, 19, 23, 24];

      function runNextStep() {
        const eps = DATA.episodes.optimal;
        if (orderPos >= OPT_ORDER.length) orderPos = 0;
        const ep = eps[OPT_ORDER[orderPos]];

        if (stepIdx === 0) {
          grid.clearPaths();
          grid.moveRobot(ep.states[0], 0, true);
          epLabelEl.textContent = `Tập ${orderPos + 1}/${eps.length} theo π*`;
          epStatusEl.className = "status-pill running";
          epStatusEl.textContent = "Đang di chuyển...";
        }

        if (stepIdx < ep.actions.length) {
          const nextState = ep.states[stepIdx + 1];
          const heading = ep.actions[stepIdx];
          grid.drawPath(ep.states.slice(0, stepIdx + 2), { color: "#16A34A", width: 7, opacity: 0.95, halo: true });
          grid.moveRobot(nextState, heading, false);
          stepIdx++;
          scheduler.after(820, runNextStep);
        } else {
          const lastState = ep.states[ep.states.length - 1];
          grid.flashCell(lastState, ep.outcome === "goal" ? "goal" : "trap");
          epStatusEl.className = "status-pill " + (ep.outcome === "goal" ? "goal" : "trap");
          epStatusEl.textContent = ep.outcome === "goal"
            ? `Tới đích (+${ep.total_reward.toFixed(2)})`
            : `Trượt bẫy (${ep.total_reward.toFixed(2)})`;
          orderPos++;
          stepIdx = 0;
          scheduler.after(1500, () => {
            for (const c of grid.cells) c.el.classList.remove("flash-trap", "flash-goal");
            runNextStep();
          });
        }
      }

      return {
        enter() {
          orderPos = 0;
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
                    <div id="s5-m-goal" class="metric-box">
                      <div class="metric-label">Thành công</div>
                      <div class="metric-value green">${fmtPct(st.success_rate)}</div>
                    </div>
                    <div id="s5-m-trap" class="metric-box">
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

          if (isAutoPlay()) {
            // 0.0s - 7.4s: Câu 1 giới thiệu π*, robot đứng sẵn ở START
            grid.moveRobot(0, 0, true);
            epStatusEl.textContent = "Sẵn sàng theo π*";
            scheduler.after(7400, runNextStep);

            // 15.1s: Câu 3 — nhấn ô (2,1) [s=1] chỉ mũi tên sang trái
            scheduler.after(15100, () => grid.setFocusCells([1], "amber"));
            // 22.5s: Câu 4 — Thành công 88.5%
            scheduler.after(22500, () => {
              grid.setFocusCells([]);
              setCue("s5-m-goal", S5_METRICS);
            });
            // 29.2s: Câu 5 — Rơi bẫy 11.5% tại (3,4) [s=14] -> (3,3) [s=10]
            scheduler.after(29200, () => {
              setCue("s5-m-trap", S5_METRICS);
              grid.setFocusCells([14, 10], "red");
            });
            // 37.5s: Câu 6 — kết luận tổng quát
            scheduler.after(37500, () => {
              setCue([], S5_METRICS);
              grid.setFocusCells([]);
            });
          } else {
            scheduler.after(550, runNextStep);
          }
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

    // 6. Đối chiếu nghiệm π* vs Chính sách tự đặt sát bẫy (s6: 119.01s)
    function scene6() {
      let gOpt = null;
      let gRisky = null;
      let pairPos = 0;
      let stepIdx = 0;
      let raceStarted = false;
      let statusOptEl = null;
      let statusRiskyEl = null;

      const OPT_THEORY = [0, 4, 8, 12, 13, 14, 15];
      const RISKY_THEORY = [0, 1, 2, 3, 7, 11, 15];
      const RACE_PAIRS = [[7, 5], [11, 1], [14, 2], [4, 3], [21, 6], [15, 7], [8, 10], [9, 16]];
      const S6_CUES = ["s6-card-opt", "s6-card-risky", "s6-conclusion"];
      const S6_STAT_ITEMS = [
        "s6-opt-v", "s6-opt-win", "s6-opt-trap", "s6-opt-to",
        "s6-risk-v", "s6-risk-win", "s6-risk-trap", "s6-risk-to",
      ];

      function animateTheoreticalPath(grid, states, color, dashed, stepDelay) {
        for (let len = 2; len <= states.length; len++) {
          scheduler.after((len - 2) * stepDelay, () => {
            grid.drawPath(states.slice(0, len), { color, dashed, width: 6, opacity: 0.85, layerId: "theory", halo: true });
          });
        }
      }

      function playDemoTrace(grid, statusEl, states, actions, color, stepMs, startHeading, endLabel, endKind, runningLabel = "Đang mô phỏng") {
        for (const c of grid.cells) c.el.classList.remove("flash-trap", "flash-goal");
        grid.drawPath([], { layerId: "live" });
        grid.moveRobot(states[0], startHeading, true);
        statusEl.className = "status-pill running";
        statusEl.textContent = runningLabel;

        for (let i = 0; i < actions.length; i++) {
          scheduler.after((i + 1) * stepMs, () => {
            if (raceStarted) return;
            grid.drawPath(states.slice(0, i + 2), { color, width: 6, opacity: 0.95, layerId: "live", halo: true });
            grid.moveRobot(states[i + 1], actions[i], false);
            if (i + 1 === actions.length) {
              if (endKind === "goal" || endKind === "trap") {
                grid.flashCell(states[states.length - 1], endKind);
              }
              statusEl.className = "status-pill " + endKind;
              statusEl.textContent = endLabel;
            }
          });
        }
      }

      function runRaceStep() {
        const epsOpt = DATA.episodes.optimal;
        const epsRisky = DATA.episodes.risky;
        const [optIdx, riskyIdx] = RACE_PAIRS[pairPos % RACE_PAIRS.length];

        const epO = epsOpt[optIdx];
        const epR = epsRisky[riskyIdx];

        if (stepIdx === 0) {
          for (const c of gOpt.cells) c.el.classList.remove("flash-trap", "flash-goal");
          for (const c of gRisky.cells) c.el.classList.remove("flash-trap", "flash-goal");
          gOpt.drawPath(OPT_THEORY, { color: "#16A34A", width: 5, opacity: 0.35, layerId: "theory" });
          gRisky.drawPath(RISKY_THEORY, { color: "#DC2626", dashed: true, width: 5, opacity: 0.4, layerId: "theory" });
          gOpt.drawPath([], { layerId: "live" });
          gRisky.drawPath([], { layerId: "live" });
          gOpt.moveRobot(epO.states[0], 0, true);
          gRisky.moveRobot(epR.states[0], 3, true);
          statusOptEl.className = "status-pill running";
          statusOptEl.textContent = `Lượt ${pairPos + 1}: Đang chạy`;
          statusRiskyEl.className = "status-pill running";
          statusRiskyEl.textContent = `Lượt ${pairPos + 1}: Đang chạy`;
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
                : "Timeout";
          }
        }

        if (!optDone || !riskyDone) {
          stepIdx++;
          scheduler.after(620, runRaceStep);
        } else {
          pairPos++;
          stepIdx = 0;
          scheduler.after(1800, runRaceStep);
        }
      }

      return {
        enter() {
          pairPos = 0;
          stepIdx = 0;
          raceStarted = false;
          const stOpt = DATA.stats.optimal;
          const stRisky = DATA.stats.risky;

          stageBody.innerHTML = `
            <div class="compare-layout">
              <div class="compare-pair">
                <div id="s6-card-opt" class="compare-card">
                  <div class="compare-card-header">
                    <span class="compare-card-title opt">Nghiệm tối ưu π* (Đi vòng an toàn)</span>
                    <span id="s6-st-opt" class="status-pill running">Đang chạy</span>
                  </div>
                  <div id="s6-grid-opt"></div>
                  <div id="s6-stats-opt" class="compare-stats">
                    <div id="s6-opt-v" class="compare-stat-item">
                      <div class="compare-stat-label">V(Start)</div>
                      <div class="compare-stat-val" style="color:var(--start)">${DATA.vi.V_star[0].toFixed(2)}</div>
                    </div>
                    <div id="s6-opt-win" class="compare-stat-item">
                      <div class="compare-stat-label">Thành công</div>
                      <div class="compare-stat-val" style="color:var(--opt)">${fmtPct(stOpt.success_rate)}</div>
                    </div>
                    <div id="s6-opt-trap" class="compare-stat-item">
                      <div class="compare-stat-label">Rơi bẫy</div>
                      <div class="compare-stat-val" style="color:var(--risky)">${fmtPct(stOpt.trap_rate)}</div>
                    </div>
                    <div id="s6-opt-to" class="compare-stat-item">
                      <div class="compare-stat-label">Timeout</div>
                      <div class="compare-stat-val" style="color:var(--muted)">${fmtPct(stOpt.timeout_rate)}</div>
                    </div>
                  </div>
                </div>

                <div id="s6-card-risky" class="compare-card">
                  <div class="compare-card-header">
                    <span class="compare-card-title risky">Chính sách tự đặt: Đi sát bẫy (Đối chứng)</span>
                    <span id="s6-st-risky" class="status-pill running">Đang chạy</span>
                  </div>
                  <div id="s6-grid-risky"></div>
                  <div id="s6-stats-risky" class="compare-stats">
                    <div id="s6-risk-v" class="compare-stat-item">
                      <div class="compare-stat-label">V(Start)</div>
                      <div class="compare-stat-val" style="color:var(--start)">${DATA.risky.V[0].toFixed(2)}</div>
                    </div>
                    <div id="s6-risk-win" class="compare-stat-item">
                      <div class="compare-stat-label">Thành công</div>
                      <div class="compare-stat-val" style="color:var(--opt)">${fmtPct(stRisky.success_rate)}</div>
                    </div>
                    <div id="s6-risk-trap" class="compare-stat-item">
                      <div class="compare-stat-label">Rơi bẫy</div>
                      <div class="compare-stat-val" style="color:var(--risky)">${fmtPct(stRisky.trap_rate)}</div>
                    </div>
                    <div id="s6-risk-to" class="compare-stat-item">
                      <div class="compare-stat-label">Timeout</div>
                      <div class="compare-stat-val" style="color:var(--muted)">${fmtPct(stRisky.timeout_rate)}</div>
                    </div>
                  </div>
                </div>
              </div>

              <div id="s6-conclusion" class="conclusion-banner">
                Thông điệp cốt lõi MDP: Đường ngắn nhất chưa chắc tối ưu — phương trình Bellman tự định lượng rủi ro để chọn lộ trình an toàn mà không cần luật né bẫy thủ công.
              </div>
            </div>
          `;

          gOpt = new GridView(document.getElementById("s6-grid-opt"), { size: 440, compact: true });
          gRisky = new GridView(document.getElementById("s6-grid-risky"), { size: 440, compact: true });
          gOpt.setPolicy(DATA.vi.pi_star, { color: "#16A34A", arrowScale: 0.9, opacity: 0.65 });
          gRisky.setPolicy(DATA.risky.policy, { color: "#DC2626", arrowScale: 0.9, opacity: 0.65 });
          statusOptEl = document.getElementById("s6-st-opt");
          statusRiskyEl = document.getElementById("s6-st-risky");

          if (isAutoPlay()) {
            gOpt.moveRobot(0, 0, true);
            gRisky.moveRobot(0, 3, true);
            statusOptEl.textContent = "Nghiệm Quy hoạch động";
            statusRiskyEl.textContent = "Chính sách tự đặt";

            // Câu #1 (0.4s - 9.75s): Giới thiệu 2 bên đặt đối chiếu cạnh nhau
            scheduler.after(4200, () => setCue("s6-card-opt", S6_CUES));
            scheduler.after(6600, () => setCue("s6-card-risky", S6_CUES));

            // Câu #2 (9.75s - 18.86s): Bên trái pi* — vẽ đường lý thuyết & robot đi đúng 6 bước
            scheduler.after(9750, () => {
              setCue("s6-card-opt", S6_CUES);
              animateTheoreticalPath(gOpt, OPT_THEORY, "#16A34A", false, 550);
              playDemoTrace(
                gOpt, statusOptEl,
                OPT_THEORY, [0, 0, 0, 3, 3, 3],
                "#16A34A", 680, 0, "Đích (6 bước lý thuyết)", "goal", "Đi lên Cột 1 → Hàng 4"
              );
            });

            // Câu #3 (18.86s - 28.93s): Bên phải tự đặt — vẽ đường lý thuyết & robot đi đúng 6 bước
            scheduler.after(18860, () => {
              setCue("s6-card-risky", S6_CUES);
              animateTheoreticalPath(gRisky, RISKY_THEORY, "#DC2626", true, 550);
              playDemoTrace(
                gRisky, statusRiskyEl,
                RISKY_THEORY, [3, 3, 3, 0, 0, 0],
                "#DC2626", 680, 3, "Đích (6 bước lý thuyết)", "goal", "Đi Hàng 1 → lên Cột 4"
              );
            });

            // Câu #4 (28.93s - 38.36s): Cùng 6 bước nhưng độ trượt 20% tạo ra khác biệt
            scheduler.after(28930, () => {
              setCue(["s6-card-opt", "s6-card-risky"], S6_CUES);
              for (const c of gOpt.cells) c.el.classList.remove("flash-trap", "flash-goal");
              for (const c of gRisky.cells) c.el.classList.remove("flash-trap", "flash-goal");
              gOpt.drawPath(OPT_THEORY, { color: "#16A34A", width: 5, opacity: 0.35, layerId: "theory" });
              gRisky.drawPath(RISKY_THEORY, { color: "#DC2626", dashed: true, width: 5, opacity: 0.35, layerId: "theory" });
              gOpt.drawPath([], { layerId: "live" });
              gRisky.drawPath([], { layerId: "live" });
              gOpt.moveRobot(0, 0, true);
              gRisky.moveRobot(0, 3, true);
              statusOptEl.className = "status-pill running";
              statusOptEl.textContent = "Độ trượt 20%/bước";
              statusRiskyEl.className = "status-pill running";
              statusRiskyEl.textContent = "Độ trượt 20%/bước";
            });
            scheduler.after(32500, () => {
              gOpt.showSlipDemo("all");
              gRisky.showSlipDemo("all");
            });

            // Câu #5 (38.36s - 50.19s): Bên trái — an toàn Cột 1, trượt sang Cột 2 quay về Cột 1, 1 rủi ro ở (3,4)
            scheduler.after(38360, () => {
              gOpt.showSlipDemo("none");
              gRisky.showSlipDemo("none");
              setCue("s6-card-opt", S6_CUES);
              gOpt.setFocusCells([0, 4, 8, 12], "green");
            });
            scheduler.after(41500, () => {
              const epSlipBack = DATA.episodes.optimal[10];
              playDemoTrace(
                gOpt, statusOptEl,
                epSlipBack.states, epSlipBack.actions,
                "#16A34A", 520, 0, "Quay về Cột 1 → Đích", "goal", "Trượt Cột 2 → quay về Cột 1"
              );
            });
            scheduler.after(42400, () => gOpt.setFocusCells([1, 5, 9], "blue"));
            scheduler.after(46500, () => gOpt.setFocusCells([14], "amber"));

            // Câu #6 (50.19s - 61.46s): Bên phải — 3 điểm sát bẫy (3,1), (4,2), (4,3) -> rơi bẫy -10
            scheduler.after(50190, () => {
              gOpt.setFocusCells([]);
              setCue("s6-card-risky", S6_CUES);
              gRisky.setFocusCells([2, 7, 11], "amber");
              const epTrap1 = DATA.episodes.risky[5];
              playDemoTrace(
                gRisky, statusRiskyEl,
                epTrap1.states, epTrap1.actions,
                "#DC2626", 600, 3, "Trượt (4,3) → Bẫy −10", "trap", "Qua 3 điểm sát bẫy"
              );
            });
            scheduler.after(56200, () => {
              gRisky.setFocusCells([6, 10], "red");
              const epTrap2 = DATA.episodes.risky[2];
              playDemoTrace(
                gRisky, statusRiskyEl,
                epTrap2.states, epTrap2.actions,
                "#DC2626", 550, 3, "Trượt (3,1) → Bẫy −10", "trap", "Rủi ro 10% vào bẫy"
              );
            });

            // Câu #7 (61.46s - 70.73s): Bên phải — trượt sớm lên vùng trên-trái -> kẹt tường trên 50 bước (Timeout)
            scheduler.after(61460, () => {
              gRisky.setFocusCells([4, 5, 8, 9, 12, 13], "amber");
              const epTimeout = DATA.episodes.risky[20];
              playDemoTrace(
                gRisky, statusRiskyEl,
                epTimeout.states.slice(0, 12), epTimeout.actions.slice(0, 11),
                "#DC2626", 500, 3, "Kẹt tường trên · Timeout (50 bước)", "timeout", "Trượt sớm lên trên-trái..."
              );
            });
            scheduler.after(65800, () => gRisky.setFocusCells([12, 13, 14], "red"));

            // Câu #8 (70.73s - 84.16s): Chạy đua thực tế + đọc từng chỉ số bên trái
            scheduler.after(70730, () => {
              raceStarted = true;
              gOpt.setFocusCells([]);
              gRisky.setFocusCells([]);
              setCue("s6-card-opt", S6_CUES);
              runRaceStep();
            });
            scheduler.after(74500, () => setCue("s6-opt-v", S6_STAT_ITEMS));
            scheduler.after(77900, () => setCue("s6-opt-win", S6_STAT_ITEMS));
            scheduler.after(80100, () => setCue("s6-opt-trap", S6_STAT_ITEMS));
            scheduler.after(81800, () => setCue("s6-opt-to", S6_STAT_ITEMS));

            // Câu #9 (84.16s - 98.23s): Đọc từng chỉ số bên phải
            scheduler.after(84160, () => {
              setCue([], S6_STAT_ITEMS);
              setCue("s6-card-risky", S6_CUES);
            });
            scheduler.after(86500, () => setCue("s6-risk-v", S6_STAT_ITEMS));
            scheduler.after(89400, () => setCue("s6-risk-win", S6_STAT_ITEMS));
            scheduler.after(92400, () => setCue("s6-risk-trap", S6_STAT_ITEMS));
            scheduler.after(95200, () => setCue("s6-risk-to", S6_STAT_ITEMS));

            // Câu #10 & #11 (98.23s - 119.01s): Thông điệp cốt lõi MDP + lời cảm ơn
            scheduler.after(98230, () => {
              setCue([], S6_STAT_ITEMS);
              setCue("s6-conclusion", S6_CUES);
            });
          } else {
            scheduler.after(600, runRaceStep);
          }
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
  const speedControlEl = document.getElementById("speed-control");

  const SPEED_OPTIONS = [0.5, 0.75, 1, 1.5, 2];
  let playbackSpeed = 1;

  const scheduler = new Scheduler(playbackSpeed);
  const autoScheduler = new Scheduler(playbackSpeed);
  const voicePlayer = new Audio();
  let voiceEnabled = Boolean(AUDIO_META);
  let currentIdx = 0;
  let autoPlay = false;
  let hintsVisible = true;

  function applyAudioSpeed() {
    voicePlayer.defaultPlaybackRate = playbackSpeed;
    voicePlayer.playbackRate = playbackSpeed;
    if ("preservesPitch" in voicePlayer) voicePlayer.preservesPitch = true;
    if ("mozPreservesPitch" in voicePlayer) voicePlayer.mozPreservesPitch = true;
    if ("webkitPreservesPitch" in voicePlayer) voicePlayer.webkitPreservesPitch = true;
  }

  voicePlayer.addEventListener("loadedmetadata", applyAudioSpeed);
  voicePlayer.addEventListener("play", applyAudioSpeed);
  stage.style.setProperty("--sim-speed", String(playbackSpeed));

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
    (idx) => goToScene(idx),
    () => autoPlay
  );

  const speedButtons = SPEED_OPTIONS.map((spd) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "speed-btn" + (spd === playbackSpeed ? " active" : "");
    btn.textContent = `${spd}x`;
    btn.title = `Tốc độ ${spd}x`;
    btn.addEventListener("click", () => setPlaybackSpeed(spd));
    if (speedControlEl) speedControlEl.appendChild(btn);
    return { spd, btn };
  });

  function setPlaybackSpeed(newSpeed) {
    if (!SPEED_OPTIONS.includes(newSpeed)) return;
    playbackSpeed = newSpeed;
    stage.style.setProperty("--sim-speed", String(newSpeed));
    scheduler.setSpeed(newSpeed);
    autoScheduler.setSpeed(newSpeed);
    applyAudioSpeed();
    for (const item of speedButtons) {
      item.btn.classList.toggle("active", item.spd === newSpeed);
    }
    updateHeader();
  }

  function stepSpeed(delta) {
    const idx = SPEED_OPTIONS.indexOf(playbackSpeed);
    const nextIdx = Math.max(0, Math.min(SPEED_OPTIONS.length - 1, idx + delta));
    setPlaybackSpeed(SPEED_OPTIONS[nextIdx]);
  }

  const dots = scenes.map((_, idx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "scene-dot";
    btn.title = `Cảnh ${idx + 1}`;
    btn.addEventListener("click", () => {
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
    autoScheduler.clearAll();
  }

  function updateHeader() {
    counterEl.textContent = `Cảnh ${currentIdx + 1}/6`;
    dots.forEach((d, i) => d.classList.toggle("active", i === currentIdx));

    if (!hintsVisible) {
      modeBadge.classList.add("hidden");
      return;
    }
    const voiceTag = voiceEnabled ? " · Có giọng đọc" : " · Tắt tiếng (M)";
    const speedTag = playbackSpeed !== 1 ? ` · ${playbackSpeed}x` : "";
    if (scheduler.paused) {
      modeBadge.textContent = "Đang tạm dừng (P)" + speedTag;
      modeBadge.className = "mode-badge paused";
    } else if (autoPlay) {
      modeBadge.textContent = "Tự động phát (A)" + voiceTag + speedTag;
      modeBadge.className = "mode-badge";
    } else if (!voiceEnabled) {
      modeBadge.textContent = "Đã tắt giọng đọc (M)" + speedTag;
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
      applyAudioSpeed();
      voicePlayer.onended = () => {
        voicePlayer.onended = null;
        if (!autoPlay || scheduler.paused) return;
        autoScheduler.after(GAP_MS, advanceAutoStep);
      };
      voicePlayer.onerror = () => {
        voicePlayer.onerror = null;
        if (!autoPlay || scheduler.paused) return;
        autoScheduler.after(durMs + GAP_MS, advanceAutoStep);
      };
      const playPromise = voicePlayer.play();
      if (playPromise && typeof playPromise.catch === "function") {
        playPromise.catch(() => {
          voicePlayer.onended = null;
          if (!autoPlay || scheduler.paused) return;
          autoScheduler.after(durMs + GAP_MS, advanceAutoStep);
        });
      }
    } else {
      autoScheduler.after(durMs + GAP_MS, advanceAutoStep);
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
    autoScheduler.resume();
    goToScene(currentIdx);
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
        if (currentIdx > 0) goToScene(currentIdx - 1);
        break;
      case "p":
      case "P":
        if (scheduler.paused) {
          scheduler.resume();
          autoScheduler.resume();
          if (autoPlay) {
            if (voiceEnabled && voicePlayer.src && voicePlayer.paused && !voicePlayer.ended) {
              applyAudioSpeed();
              voicePlayer.play().catch(() => {});
            } else if (autoScheduler.timers.size === 0) {
              playSegmentAudio(scenes[currentIdx].currentSegmentKey());
            }
          }
        } else {
          scheduler.pause();
          autoScheduler.pause();
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
      case "-":
      case "_":
      case "[":
        stepSpeed(-1);
        break;
      case "+":
      case "=":
      case "]":
        stepSpeed(1);
        break;
      case "0":
        setPlaybackSpeed(1);
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
