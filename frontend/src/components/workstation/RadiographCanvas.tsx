import React, { useRef, useState, useEffect, useCallback } from 'react';
import { Finding } from '../../api/types';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  Eye,
  EyeOff,
  Layers,
  Hand,
  RotateCcw,
  Square,
  Trash2,
} from 'lucide-react';

interface RadiographCanvasProps {
  imageUrl: string;
  findings: Finding[];
  selectedFindingId?: string | null;
  onSelectFinding?: (findingId: string) => void;
  selectedToothFdi?: number | null;
  height?: number | string;
  originalWidth?: number;
  originalHeight?: number;
  onCreateRegion?: (bbox: { x_min: number; y_min: number; x_max: number; y_max: number }) => void;
  onDeleteAnnotation?: (findingId: string) => void;
}

export const RadiographCanvas: React.FC<RadiographCanvasProps> = ({
  imageUrl,
  findings = [],
  selectedFindingId,
  onSelectFinding,
  selectedToothFdi,
  height = '100%',
  originalWidth,
  originalHeight,
  onCreateRegion,
  onDeleteAnnotation,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  // Pan & Zoom state
  const [scale, setScale] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const dragStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const panStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Viewport / Cursor Telemetry
  const [cursorPos, setCursorPos] = useState<{ x: number; y: number } | null>(null);
  const [naturalSize, setNaturalSize] = useState<{ w: number; h: number }>({ w: 0, h: 0 });

  // Overlay Visibility & Hover State
  const [showOverlays, setShowOverlays] = useState<boolean>(true);
  const [hoveredFindingId, setHoveredFindingId] = useState<string | null>(null);
  const [enhancedDisplay, setEnhancedDisplay] = useState<boolean>(false);
  const [hasAutoFitted, setHasAutoFitted] = useState<boolean>(false);

  // Manual Region Drawing State
  const [isDrawingMode, setIsDrawingMode] = useState<boolean>(false);
  const [drawingRect, setDrawingRect] = useState<{ startX: number; startY: number; curX: number; curY: number } | null>(null);

  // Zoom handlers
  const handleZoomIn = () => setScale((s) => Math.min(5, +(s * 1.2).toFixed(2)));
  const handleZoomOut = () => setScale((s) => Math.max(0.2, +(s / 1.2).toFixed(2)));
  const handleResetZoom = () => {
    setScale(1);
    setPan({ x: 0, y: 0 });
  };

  const handleFit = useCallback(() => {
    if (!containerRef.current || !naturalSize.w) return;
    const cw = containerRef.current.clientWidth - 32;
    const ch = containerRef.current.clientHeight - 48;
    const s = Math.min(cw / naturalSize.w, ch / naturalSize.h, 1);
    setScale(+s.toFixed(2));
    setPan({ x: 0, y: 0 });
  }, [naturalSize.w, naturalSize.h]);

  // Automatically fit on initial load of new image
  useEffect(() => {
    setHasAutoFitted(false);
  }, [imageUrl]);

  useEffect(() => {
    if (naturalSize.w > 0 && !hasAutoFitted) {
      handleFit();
      setHasAutoFitted(true);
    }
  }, [naturalSize.w, naturalSize.h, hasAutoFitted, handleFit]);

  // Non-passive wheel zoom (prevents page scrolling while zooming X-ray)
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      e.stopPropagation();
      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.87;
      setScale((prevScale) => {
        return Math.max(0.2, Math.min(5, +(prevScale * zoomFactor).toFixed(2)));
      });
    };

    el.addEventListener('wheel', onWheel, { passive: false });
    return () => {
      el.removeEventListener('wheel', onWheel);
    };
  }, []);

  // Sync naturalSize on imageUrl change or if image is already cached
  useEffect(() => {
    if (imageRef.current) {
      if (imageRef.current.complete && imageRef.current.naturalWidth > 0) {
        setNaturalSize({
          w: imageRef.current.naturalWidth,
          h: imageRef.current.naturalHeight,
        });
      }
    }
  }, [imageUrl]);

  // Pointer Drag Pan handlers with pointer capture (smooth, never loses drag)
  const handlePointerDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    // Don't drag if clicking buttons
    const target = e.target as HTMLElement | SVGElement;
    if (target.closest('button')) return;

    // Drawing Region Mode
    if (isDrawingMode && imageRef.current) {
      const rect = imageRef.current.getBoundingClientRect();
      const relX = Math.round((e.clientX - rect.left) / scale);
      const relY = Math.round((e.clientY - rect.top) / scale);
      setDrawingRect({ startX: relX, startY: relY, curX: relX, curY: relY });
      try {
        e.currentTarget.setPointerCapture(e.pointerId);
      } catch {}
      return;
    }

    // If clicked inside SVG g element (finding box or label), don't pan
    if (target.closest('g[data-finding]')) return;
    if (target.tagName === 'rect' || target.tagName === 'text' || target.tagName === 'path') return;

    setIsDragging(true);
    dragStartRef.current = { x: e.clientX, y: e.clientY };
    panStartRef.current = { ...pan };
    try {
      e.currentTarget.setPointerCapture(e.pointerId);
    } catch {}
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (imageRef.current && naturalSize.w) {
      const rect = imageRef.current.getBoundingClientRect();
      const relX = Math.round((e.clientX - rect.left) / scale);
      const relY = Math.round((e.clientY - rect.top) / scale);
      if (relX >= 0 && relX <= naturalSize.w && relY >= 0 && relY <= naturalSize.h) {
        setCursorPos({ x: relX, y: relY });
      } else {
        setCursorPos(null);
      }
    }

    // Active Drawing Mode
    if (isDrawingMode && drawingRect && imageRef.current) {
      const rect = imageRef.current.getBoundingClientRect();
      const relX = Math.round((e.clientX - rect.left) / scale);
      const relY = Math.round((e.clientY - rect.top) / scale);
      setDrawingRect((prev) => (prev ? { ...prev, curX: relX, curY: relY } : null));
      return;
    }

    if (!isDragging) return;
    const dx = e.clientX - dragStartRef.current.x;
    const dy = e.clientY - dragStartRef.current.y;
    setPan({
      x: panStartRef.current.x + dx,
      y: panStartRef.current.y + dy,
    });
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    // Complete Drawing Region
    if (isDrawingMode && drawingRect) {
      const x_min = Math.min(drawingRect.startX, drawingRect.curX);
      const x_max = Math.max(drawingRect.startX, drawingRect.curX);
      const y_min = Math.min(drawingRect.startY, drawingRect.curY);
      const y_max = Math.max(drawingRect.startY, drawingRect.curY);
      if (x_max - x_min > 12 && y_max - y_min > 12 && onCreateRegion) {
        onCreateRegion({ x_min, y_min, x_max, y_max });
      }
      setDrawingRect(null);
      try {
        e.currentTarget.releasePointerCapture(e.pointerId);
      } catch {}
      return;
    }

    if (isDragging) {
      setIsDragging(false);
      try {
        e.currentTarget.releasePointerCapture(e.pointerId);
      } catch {}
    }
  };

  // Auto-fit on initial load
  useEffect(() => {
    if (naturalSize.w > 0) {
      handleFit();
    }
  }, [naturalSize.w, naturalSize.h, handleFit]);

  // Visual state engine — returns stroke, fill and casing colors per finding state
  const getFindingVisualState = (
    f: Finding,
    isSelected: boolean,
    isToothSelected: boolean,
    isHovered: boolean
  ) => {
    const isFocused = isSelected || isToothSelected || isHovered;
    const isManual = (f as any).model_id === 'clinician_manual' || (f as any).model_id === 'manual_clinician';
    const status = f.review_status;

    // State priority: manual annotation > dismissed > confirmed > selected > AI-candidate
    if (isManual) {
      return {
        strokeColor: '#0284C7', // High-contrast Blue / Cyan for manual annotations
        fillColor: isFocused ? 'rgba(2, 132, 199, 0.30)' : 'rgba(2, 132, 199, 0.14)',
        casingColor: '#0C4A6E',
        strokeDash: 'none',
        strokeWidth: isFocused ? 3.5 : 2.5,
      };
    }
    if (status === 'rejected') {
      return {
        strokeColor: '#94A3B8',
        fillColor: 'rgba(148, 163, 184, 0.10)',
        casingColor: '#475569',
        strokeDash: '6 4',
        strokeWidth: 2.0,
      };
    }
    if (status === 'confirmed') {
      return {
        strokeColor: '#16A34A',
        fillColor: isFocused ? 'rgba(22, 163, 74, 0.20)' : 'rgba(22, 163, 74, 0.08)',
        casingColor: '#14532D',
        strokeDash: 'none',
        strokeWidth: isFocused ? 3.5 : 2.0,
      };
    }
    if (isSelected) {
      return {
        strokeColor: '#0284C7',
        fillColor: 'rgba(2, 132, 199, 0.22)',
        casingColor: '#0C4A6E',
        strokeDash: 'none',
        strokeWidth: 3.5,
      };
    }
    // AI candidate — BRIGHT YELLOW/AMBER
    return {
      strokeColor: '#FACC15',
      fillColor: isFocused ? 'rgba(250, 204, 21, 0.24)' : 'rgba(250, 204, 21, 0.10)',
      casingColor: '#78350F',
      strokeDash: 'none',
      strokeWidth: isFocused ? 3.5 : 2.5,
    };
  };

  // Label badge color per state
  const getBadgeColor = (f: Finding) => {
    if ((f as any).model_id === 'clinician_manual' || (f as any).model_id === 'manual_clinician') return '#0284C7';
    if (f.review_status === 'rejected') return '#64748B';
    if (f.review_status === 'confirmed') return '#16A34A';
    return '#B45309'; // amber-700 for candidate
  };

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        maxWidth: '100%',
        minWidth: 0,
        height: typeof height === 'number' ? `${height}px` : height,
        minHeight: '440px',
        background: '#0B0F12',
        overflow: 'hidden',
        userSelect: 'none',
        display: 'flex',
        flexDirection: 'column',
        borderRadius: '6px',
        border: '1px solid #E2E6E3',
        touchAction: 'none',
        cursor: isDrawingMode ? 'crosshair' : (isDragging ? 'grabbing' : 'grab'),
      }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      {/* Top Floating Viewport Toolbar (Light Medical Frame) */}
      <div
        style={{
          position: 'absolute',
          top: '12px',
          left: '12px',
          right: '12px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          zIndex: 20,
          pointerEvents: 'none',
        }}
      >
        {/* Left Toolbar Cluster: Overlay Visibility + Annotate Region */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {/* Overlay Visibility Toggle */}
          <div
            style={{
              display: 'flex',
              gap: '6px',
              background: 'rgba(255, 255, 255, 0.94)',
              padding: '4px 8px',
              borderRadius: '4px',
              border: '1px solid #E2E6E3',
              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              pointerEvents: 'auto',
              alignItems: 'center',
            }}
          >
            <button
              onClick={() => setShowOverlays(!showOverlays)}
              style={{
                padding: '4px 8px',
                fontSize: '11px',
                fontWeight: 600,
                borderRadius: '3px',
                border: 'none',
                background: showOverlays ? '#3E6B61' : '#EDF2EE',
                color: showOverlays ? '#FFFFFF' : '#4E5A58',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 120ms ease',
              }}
            >
              {showOverlays ? <Eye size={12} /> : <EyeOff size={12} />}
              {showOverlays ? 'Overlays Active' : 'Overlays Hidden'}
            </button>
            <span style={{ fontSize: '11px', color: '#7A8885', padding: '0 4px' }}>
              {findings.length}
            </span>
          </div>
        </div>

        {/* Zoom Controls & Hand Tool Bar */}
        <div
          style={{
            display: 'flex',
            gap: '6px',
            alignItems: 'center',
            pointerEvents: 'auto',
          }}
        >
          {/* Hand Pan Tool Indicator */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: isDragging ? '#3E6B61' : 'rgba(255, 255, 255, 0.94)',
              color: isDragging ? '#FFFFFF' : '#2C574C',
              padding: '4px 10px',
              borderRadius: '4px',
              border: '1px solid #E2E6E3',
              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              fontSize: '11px',
              fontWeight: 600,
              transition: 'all 120ms ease',
            }}
            title="Click and drag anywhere on the radiograph to pan smoothly. Scroll mouse wheel to zoom."
          >
            <Hand size={12} />
            <span>{isDragging ? 'Panning...' : 'Pan & Zoom Mode'}</span>
          </div>

          <div
            style={{
              display: 'flex',
              gap: '4px',
              background: 'rgba(255, 255, 255, 0.94)',
              padding: '4px 8px',
              borderRadius: '4px',
              border: '1px solid #E2E6E3',
              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              alignItems: 'center',
            }}
          >
            <button
              onClick={handleZoomOut}
              style={{
                color: '#384543',
                background: 'transparent',
                border: 'none',
                padding: '4px 6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                borderRadius: '3px',
              }}
              title="Zoom Out (-20%)"
            >
              <ZoomOut size={13} />
            </button>
            <span
              style={{
                fontSize: '11px',
                color: '#2A3634',
                fontFamily: 'monospace',
                fontWeight: 600,
                minWidth: '42px',
                textAlign: 'center',
              }}
            >
              {Math.round(scale * 100)}%
            </span>
            <button
              onClick={handleZoomIn}
              style={{
                color: '#384543',
                background: 'transparent',
                border: 'none',
                padding: '4px 6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                borderRadius: '3px',
              }}
              title="Zoom In (+20%)"
            >
              <ZoomIn size={13} />
            </button>
            <div style={{ width: '1px', height: '14px', background: '#E2E6E3', margin: '0 2px' }} />
            <button
              onClick={handleFit}
              style={{
                color: '#384543',
                background: 'transparent',
                border: 'none',
                padding: '4px 6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                borderRadius: '3px',
                fontSize: '11px',
                fontWeight: 600,
                gap: '3px',
              }}
              title="Fit to Screen (View entire radiograph)"
            >
              <Minimize2 size={13} />
              <span>Fit</span>
            </button>
            <button
              onClick={handleResetZoom}
              style={{
                color: scale === 1 ? '#0F766E' : '#384543',
                background: scale === 1 ? '#E2ECE8' : 'transparent',
                border: 'none',
                padding: '4px 6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                borderRadius: '3px',
                fontSize: '11px',
                fontWeight: 600,
                gap: '3px',
              }}
              title="1:1 Actual Resolution (100% Pixels)"
            >
              <Maximize2 size={13} />
              <span>1:1</span>
            </button>
            <div style={{ width: '1px', height: '14px', background: '#E2E6E3', margin: '0 2px' }} />
            <button
              onClick={() => setEnhancedDisplay(!enhancedDisplay)}
              style={{
                color: enhancedDisplay ? '#FFFFFF' : '#384543',
                background: enhancedDisplay ? '#282b4a' : 'transparent',
                border: 'none',
                padding: '3px 7px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                borderRadius: '3px',
                fontSize: '10.5px',
                fontWeight: 600,
              }}
              title="Display enhancement toggle: Boosts micro-contrast for chairside inspection (original diagnostic pixels remain unchanged)"
            >
              {enhancedDisplay ? 'Contrast: ON' : 'Enhance'}
            </button>
          </div>
        </div>
      </div>

      {/* Main Radiograph Canvas Area */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: isDragging ? 'grabbing' : 'grab',
          position: 'relative',
        }}
      >
        <div
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`,
            transformOrigin: 'center center',
            transition: isDragging ? 'none' : 'transform 80ms ease-out',
            position: 'relative',
            display: 'inline-block',
          }}
        >
          {/* Base Radiograph Image (Authentic Grayscale, Aspect-Preserved, High-Sharpness) */}
          <img
            ref={imageRef}
            src={imageUrl}
            alt="Panoramic Dental Radiograph"
            draggable={false}
            onDragStart={(e) => e.preventDefault()}
            onLoad={(e) => {
              const img = e.currentTarget;
              setNaturalSize({ w: img.naturalWidth, h: img.naturalHeight });
            }}
            style={{
              display: 'block',
              maxWidth: 'none',
              filter: enhancedDisplay
                ? 'contrast(1.32) brightness(1.04) saturate(0)'
                : 'contrast(1.05) brightness(0.98)',
              imageRendering: scale > 1.8 ? 'pixelated' : 'auto',
              borderRadius: '2px',
              border: '1px solid rgba(255, 255, 255, 0.25)',
              boxShadow: '0 4px 16px rgba(0,0,0,0.6)',
              userSelect: 'none',
              pointerEvents: 'none',
            }}
          />

          {/* SVG Overlay Layer for Findings */}
          {naturalSize.w > 0 && showOverlays && (() => {
            // Determine coordinate space for findings
            // Findings can be in original full-image coordinates (e.g. 2872x1316)
            // while the preview raster image is downscaled (e.g. 1400x641).
            const maxX = findings.reduce((max, f) => {
              const b = f.bounding_box || (f as any).bbox;
              return b ? Math.max(max, b.x_max) : max;
            }, 0);
            const maxY = findings.reduce((max, f) => {
              const b = f.bounding_box || (f as any).bbox;
              return b ? Math.max(max, b.y_max) : max;
            }, 0);

            const coordW = originalWidth || (maxX > naturalSize.w && naturalSize.w > 0 ? (maxX > 2000 ? Math.round(maxX * 1.05) : maxX) : naturalSize.w);
            const coordH = originalHeight || (maxY > naturalSize.h && naturalSize.h > 0 ? (maxY > 1000 ? Math.round(maxY * 1.05) : maxY) : naturalSize.h);
            const scaleRatio = naturalSize.w > 0 && coordW > 0 ? coordW / naturalSize.w : 1;

            return (
              <svg
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '100%',
                  pointerEvents: 'none', // SVG root is passthrough; individual g[data-finding] elements have pointerEvents:auto
                  overflow: 'visible',
                }}
                viewBox={`0 0 ${coordW} ${coordH}`}
                preserveAspectRatio="none"
              >
                {[...findings]
                  .sort((a, b) => {
                    const aFocused = a.finding_id === selectedFindingId || (selectedToothFdi && a.tooth_fdi === selectedToothFdi) || a.finding_id === hoveredFindingId ? 1 : 0;
                    const bFocused = b.finding_id === selectedFindingId || (selectedToothFdi && b.tooth_fdi === selectedToothFdi) || b.finding_id === hoveredFindingId ? 1 : 0;
                    return aFocused - bFocused;
                  })
                  .map((f) => {
                    const isSelected = selectedFindingId === f.finding_id;
                    const isToothSelected = Boolean(selectedToothFdi && f.tooth_fdi === selectedToothFdi);
                    const isHovered = hoveredFindingId === f.finding_id;
                    const isFocused = isSelected || isToothSelected || isHovered;
                    const isAnyFocused = Boolean(selectedFindingId || selectedToothFdi || hoveredFindingId);

                    const vs = getFindingVisualState(f, isSelected, isToothSelected, isHovered);
                    const globalOpacity = !isAnyFocused || isFocused ? 1.0 : (f.review_status === 'rejected' ? 0.35 : 0.5);
                    const sw = vs.strokeWidth * scaleRatio;

                    const bbox = f.bounding_box || (f as any).bbox;
                    if (!bbox) return null;

                    const { x_min, y_min, x_max, y_max } = bbox;
                    const width = x_max - x_min;
                    const height = y_max - y_min;

                    // Polygon mask support (from segmentation models)
                    const polyPoints: Array<[number, number]> | null = (() => {
                      const seg = (f as any).segmentation_mask;
                      const poly = (f as any).polygon;
                      const raw = seg?.polygon_points || poly?.points;
                      if (!Array.isArray(raw)) return null;
                      const valid: Array<[number, number]> = [];
                      for (const p of raw) {
                        if (p && typeof p.x === 'number' && typeof p.y === 'number' && !isNaN(p.x) && !isNaN(p.y)) {
                          valid.push([p.x, p.y]);
                        } else if (Array.isArray(p) && typeof p[0] === 'number' && typeof p[1] === 'number' && !isNaN(p[0]) && !isNaN(p[1])) {
                          valid.push([p[0], p[1]]);
                        }
                      }
                      return valid.length >= 3 ? valid : null;
                    })();

                    return (
                      <g
                        key={f.finding_id}
                        data-finding={f.finding_id}
                        style={{
                          pointerEvents: 'auto',
                          cursor: 'pointer',
                          opacity: globalOpacity,
                          transition: 'opacity 150ms ease',
                        }}
                        onMouseEnter={() => setHoveredFindingId(f.finding_id)}
                        onMouseLeave={() => setHoveredFindingId(null)}
                        onPointerDown={(e) => { e.stopPropagation(); }}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onSelectFinding) onSelectFinding(f.finding_id);
                        }}
                      >
                        {/* Polygon mask overlay (segmentation) */}
                        {polyPoints && polyPoints.length > 2 && (
                          <>
                            {/* Outer dark casing for visibility on bright enamel */}
                            <polygon
                              points={polyPoints.map(([x, y]) => `${x},${y}`).join(' ')}
                              fill={vs.fillColor}
                              stroke={vs.casingColor}
                              strokeWidth={(sw + 3) * scaleRatio}
                              strokeLinejoin="round"
                            />
                            {/* Inner bright color stroke */}
                            <polygon
                              points={polyPoints.map(([x, y]) => `${x},${y}`).join(' ')}
                              fill="none"
                              stroke={vs.strokeColor}
                              strokeWidth={sw}
                              strokeLinejoin="round"
                              strokeDasharray={vs.strokeDash !== 'none' ? vs.strokeDash : undefined}
                            />
                          </>
                        )}

                        {/* Dual-stroke bounding box for maximum visibility on dark AND bright areas */}
                        {/* Outer casing (dark border so yellow is visible on bright enamel) */}
                        <rect
                          x={x_min - 1.5 * scaleRatio}
                          y={y_min - 1.5 * scaleRatio}
                          width={width + 3 * scaleRatio}
                          height={height + 3 * scaleRatio}
                          fill="none"
                          stroke={vs.casingColor}
                          strokeWidth={(sw + 2.5) * scaleRatio}
                          strokeOpacity={0.65}
                          rx={4 * scaleRatio}
                        />
                        {/* Inner bright color rect */}
                        <rect
                          x={x_min}
                          y={y_min}
                          width={width}
                          height={height}
                          fill={vs.fillColor}
                          stroke={vs.strokeColor}
                          strokeWidth={sw}
                          strokeDasharray={vs.strokeDash !== 'none' ? vs.strokeDash : undefined}
                          rx={3 * scaleRatio}
                        />

                        {/* Corner Caliper Reticles — bright yellow/state color */}
                        {(['tl', 'tr', 'bl', 'br'] as const).map((corner) => {
                          const arm = 10 * scaleRatio;
                          let d = '';
                          if (corner === 'tl') d = `M ${x_min} ${y_min + arm} L ${x_min} ${y_min} L ${x_min + arm} ${y_min}`;
                          if (corner === 'tr') d = `M ${x_max - arm} ${y_min} L ${x_max} ${y_min} L ${x_max} ${y_min + arm}`;
                          if (corner === 'bl') d = `M ${x_min} ${y_max - arm} L ${x_min} ${y_max} L ${x_min + arm} ${y_max}`;
                          if (corner === 'br') d = `M ${x_max - arm} ${y_max} L ${x_max} ${y_max} L ${x_max} ${y_max - arm}`;
                          return (
                            <g key={corner}>
                              <path d={d} stroke={vs.casingColor} strokeWidth={4 * scaleRatio} fill="none" strokeOpacity={0.6} />
                              <path d={d} stroke={vs.strokeColor} strokeWidth={2.5 * scaleRatio} fill="none" />
                            </g>
                          );
                        })}

                        {/* Floating Label Badge — FDI tooth number, pathology, confidence */}
                        {(() => {
                          const toothNum = f.tooth_fdi ? `FDI #${f.tooth_fdi}` : 'General';
                          const pathName = f.pathology_class.replace(/_/g, ' ');
                          const confPct = Math.round((f.confidence || 0) * 100);
                          const labelText = isFocused
                            ? `${toothNum} · ${pathName} ${confPct}%`
                            : `${toothNum} · ${pathName}`;

                          const charW = 6.8 * scaleRatio;
                          const badgeW = labelText.length * charW + 16 * scaleRatio;
                          const badgeH = 19 * scaleRatio;
                          const badgeY = Math.max(badgeH + 4 * scaleRatio, y_min - 2 * scaleRatio);
                          const badgeColor = getBadgeColor(f);

                          return (
                            <g transform={`translate(${x_min}, ${badgeY})`}>
                              {/* Badge shadow/casing */}
                              <rect
                                x={-1}
                                y={-badgeH - 1}
                                width={badgeW + 2}
                                height={badgeH + 2}
                                fill="#000000"
                                rx={4 * scaleRatio}
                                opacity={0.5}
                              />
                              <rect
                                x={0}
                                y={-badgeH}
                                width={badgeW}
                                height={badgeH}
                                fill={badgeColor}
                                rx={4 * scaleRatio}
                              />
                              <text
                                x={6 * scaleRatio}
                                y={-(5 * scaleRatio)}
                                fill="#FFFFFF"
                                fontSize={Math.max(9, (isFocused ? 10.5 : 9.5) * scaleRatio)}
                                fontWeight="700"
                                fontFamily="system-ui, -apple-system, sans-serif"
                              >
                                {labelText}
                              </text>
                            </g>
                          );
                        })()}
                      </g>
                    );
                  })}
              </svg>
            );
          })()}
        </div>
      </div>

      {/* Bottom Telemetry Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '6px 14px',
          background: 'rgba(255, 255, 255, 0.95)',
          borderTop: '1px solid #E2E6E3',
          fontSize: '11px',
          color: '#6E7C79',
          fontFamily: 'monospace',
        }}
      >
        <div style={{ display: 'flex', gap: '16px' }}>
          <span>
            Dimensions: <strong>{naturalSize.w ? `${naturalSize.w} × ${naturalSize.h} px` : 'Loading...'}</strong>
          </span>
          {cursorPos && (
            <span>
              Cursor: X: <strong>{cursorPos.x}</strong>, Y: <strong>{cursorPos.y}</strong>
            </span>
          )}
        </div>
        <div>
          <span>Scroll to zoom • Click-drag to pan • Click box to inspect</span>
        </div>
      </div>
    </div>
  );
};
