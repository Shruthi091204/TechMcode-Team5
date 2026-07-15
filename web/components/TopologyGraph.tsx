"use client";

/* eslint-disable @typescript-eslint/no-explicit-any */

import React, { useEffect, useRef, useState } from "react";
import cytoscape from "cytoscape";
import { Component, Dependency, IncidentReport } from "../lib/types";

interface TopologyGraphProps {
  topology: { components: Component[]; dependencies: Dependency[] };
  incident: IncidentReport;
  highlightActive?: boolean;
  expandedTiers?: string[];
  onNodeClick?: (nodeId: string, isCluster: boolean, tier: string | null) => void;
}

export default function TopologyGraph({
  topology,
  incident,
  highlightActive = true,
  expandedTiers = [],
  onNodeClick
}: TopologyGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [rootPos, setRootPos] = useState({ x: -999, y: -999 });

  const activeHypothesis = incident.hypotheses.find((h) => h.rank === 1);
  const rootCauseId = activeHypothesis?.root_cause_component || "";
  const pathNodes = React.useMemo(() => activeHypothesis?.topology_path || [], [activeHypothesis?.topology_path]);

  // Determine active tiers (which tiers are in the path)
  const pathTiers = React.useMemo(() => {
    if (!highlightActive) return new Set<string>();
    const pathComps = topology.components.filter(
      (c) => pathNodes.includes(c.component_id) || c.component_id === rootCauseId
    );
    return new Set(pathComps.map((c) => c.tier));
  }, [topology.components, pathNodes, rootCauseId, highlightActive]);

  useEffect(() => {
    if (!containerRef.current) return;

    // Determine path edges
    const pathEdges = new Set<string>();
    for (let i = 0; i < pathNodes.length - 1; i++) {
      pathEdges.add(`${pathNodes[i]}-${pathNodes[i + 1]}`);
      pathEdges.add(`${pathNodes[i + 1]}-${pathNodes[i]}`);
    }

    // Build elements
    const elements: cytoscape.ElementDefinition[] = [];
    const expandedComponents = new Set<string>();

    const tierOrder = ["edge", "network", "web", "app", "data"];
    const presetPositions: Record<string, { x: number; y: number }> = {};

    tierOrder.forEach((tier) => {
      const tierComps = topology.components.filter((c) => c.tier === tier);
      if (tierComps.length === 0) return;

      const isExpanded = expandedTiers.includes(tier) || pathTiers.has(tier);

      if (!isExpanded) {
        // Entire tier collapsed as one generic cluster node
        const clusterId = `tier-cluster-${tier}`;
        presetPositions[clusterId] = {
          x: (tierOrder.indexOf(tier) + 1) * 160,
          y: 200
        };
        elements.push({
          data: {
            id: clusterId,
            label: `${tier.toUpperCase()} (${tierComps.length})`,
            tier,
            isCluster: true,
            isRoot: false,
            isOnPath: false,
            isDecoy: false,
          }
        });
      } else {
        // Tier is partially expanded (path nodes individual, rest grouped in "others" cluster)
        const pathComps = tierComps.filter(
          (c) => highlightActive && (pathNodes.includes(c.component_id) || c.component_id === rootCauseId)
        );
        const otherComps = tierComps.filter(
          (c) => !highlightActive || (!pathNodes.includes(c.component_id) && c.component_id !== rootCauseId)
        );

        let verticalIndex = 0;

        // Render path components individually
        pathComps.forEach((comp) => {
          expandedComponents.add(comp.component_id);
          const isRoot = highlightActive && comp.component_id === rootCauseId;
          const isOnPath = highlightActive && pathNodes.includes(comp.component_id);
          const isDecoy = highlightActive && (comp.component_id === "web-05" || comp.component_id === "cache-02");

          presetPositions[comp.component_id] = {
            x: (tierOrder.indexOf(tier) + 1) * 160,
            y: (verticalIndex + 1) * 90
          };
          verticalIndex++;

          elements.push({
            data: {
              id: comp.component_id,
              label: comp.component_id,
              tier,
              isCluster: false,
              isRoot,
              isOnPath,
              isDecoy,
            }
          });
        });

        // Collapse remaining non-path components of this tier into "others" cluster
        if (otherComps.length > 0) {
          const othersClusterId = `tier-cluster-${tier}-others`;
          presetPositions[othersClusterId] = {
            x: (tierOrder.indexOf(tier) + 1) * 160,
            y: (verticalIndex + 1) * 90
          };

          elements.push({
            data: {
              id: othersClusterId,
              label: `${tier.toUpperCase()} (${otherComps.length} others)`,
              tier,
              isCluster: true,
              isRoot: false,
              isOnPath: false,
              isDecoy: false,
              isOthersCluster: true,
            }
          });
        }
      }
    });

    // Add edges (mapping source/target to cluster nodes if collapsed)
    const addedEdges = new Set<string>();

    topology.dependencies.forEach((dep) => {
      const srcComp = topology.components.find((c) => c.component_id === dep.source_id);
      const tgtComp = topology.components.find((c) => c.component_id === dep.target_id);
      if (!srcComp || !tgtComp) return;

      const srcTier = srcComp.tier;
      const tgtTier = tgtComp.tier;

      // Determine source node ID
      let sourceMapped = dep.source_id;
      const isSrcExpanded = expandedTiers.includes(srcTier) || pathTiers.has(srcTier);
      if (!isSrcExpanded) {
        sourceMapped = `tier-cluster-${srcTier}`;
      } else {
        const isSrcPath = highlightActive && (pathNodes.includes(dep.source_id) || dep.source_id === rootCauseId);
        if (!isSrcPath) {
          sourceMapped = `tier-cluster-${srcTier}-others`;
        }
      }

      // Determine target node ID
      let targetMapped = dep.target_id;
      const isTgtExpanded = expandedTiers.includes(tgtTier) || pathTiers.has(tgtTier);
      if (!isTgtExpanded) {
        targetMapped = `tier-cluster-${tgtTier}`;
      } else {
        const isTgtPath = highlightActive && (pathNodes.includes(dep.target_id) || dep.target_id === rootCauseId);
        if (!isTgtPath) {
          targetMapped = `tier-cluster-${tgtTier}-others`;
        }
      }

      if (sourceMapped !== targetMapped) {
        const edgeId = `${sourceMapped}-${targetMapped}`;
        if (!addedEdges.has(edgeId)) {
          addedEdges.add(edgeId);

          const rawEdgeId = `${dep.source_id}-${dep.target_id}`;
          const isOnPath = highlightActive && pathEdges.has(rawEdgeId) && expandedComponents.has(dep.source_id) && expandedComponents.has(dep.target_id);

          // If either node is a cluster node (contains "cluster"), edge is dimmed to 0.3
          const isDimmed = sourceMapped.includes("cluster") || targetMapped.includes("cluster");

          elements.push({
            data: {
              id: edgeId,
              source: sourceMapped,
              target: targetMapped,
              isOnPath,
              isDimmed,
            },
          });
        }
      }
    });

    // BFS hop distance from root cause node
    const hopDistances: Record<string, number> = {};
    if (rootCauseId) {
      hopDistances[rootCauseId] = 0;
      const queue: string[] = [rootCauseId];
      const adj: Record<string, string[]> = {};
      topology.components.forEach(c => {
        adj[c.component_id] = [];
      });
      topology.dependencies.forEach(dep => {
        if (!adj[dep.source_id]) adj[dep.source_id] = [];
        adj[dep.source_id].push(dep.target_id);
        if (!adj[dep.target_id]) adj[dep.target_id] = [];
        adj[dep.target_id].push(dep.source_id);
      });

      let head = 0;
      while (head < queue.length) {
        const u = queue[head++];
        const d = hopDistances[u];
        const neighbors = adj[u] || [];
        for (const v of neighbors) {
          if (hopDistances[v] === undefined) {
            hopDistances[v] = d + 1;
            queue.push(v);
          }
        }
      }
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      boxSelectionEnabled: false,
      autounselectify: true,
      layout: {
        name: "preset",
        positions: (node: any) => {
          return presetPositions[node.id()];
        },
      } as any,
      style: [
        {
          selector: "node",
          style: {
            "background-color": (ele: any) => {
              const data = ele.data();
              if (data.isCluster) return "#1E8449"; // healthy cluster of unaffected nodes
              if (data.isRoot && highlightActive) return "#E50914"; // --accent-red
              if (data.isRoot) return "#5c050a";
              if (data.isOnPath) {
                const dist = hopDistances[data.id] ?? 99;
                if (dist === 1) return "#FFA53B"; // --accent-amber
                if (dist === 2) return "#F5D547"; // --accent-yellow
                return "#F5D547";
              }

              return "#1E8449"; // healthy / unaffected node
            },
            label: "data(label)",
            color: (ele: any) => {
              const data = ele.data();
              if (data.isRoot && highlightActive) return "#E50914";
              if (data.isOnPath) {
                const dist = hopDistances[data.id] ?? 99;
                if (dist === 1) return "#FFA53B";
                if (dist === 2) return "#F5D547";
              }
              return "#FFFFFF";
            },
            opacity: (ele: any) => {
              const data = ele.data();
              if (!highlightActive) return 1.0;

              if (data.isCluster) {
                return pathTiers.has(data.tier) && !data.isOthersCluster ? 1.0 : 0.3;
              }
              const isOnPath = data.isRoot || pathNodes.includes(data.id);
              return isOnPath ? 1.0 : 0.3;
            },
            "font-family": "var(--font-inter), sans-serif",
            "font-size": "10px",
            "font-weight": "600",
            "text-valign": "bottom",
            "text-margin-y": 6,
            width: (ele: any) => (ele.data("isCluster") ? "32px" : "24px"),
            height: (ele: any) => (ele.data("isCluster") ? "32px" : "24px"),
            "border-style": (ele: any) => {
              const data = ele.data();
              return data.isDecoy ? "dashed" : "solid";
            },
            "border-width": (ele: any) => {
              const data = ele.data();
              if (data.isRoot) return "3px";
              if (data.isCluster) return "1.5px";
              return "1.5px";
            },
            "border-color": (ele: any) => {
              const data = ele.data();
              if (data.isCluster) return pathTiers.has(data.tier) && !data.isOthersCluster ? "#FFA53B" : "#2A2A2E";
              if (data.isRoot && highlightActive) return "#E50914";
              if (data.isRoot) return "#5c050a";
              if (data.isOnPath) {
                const dist = hopDistances[data.id] ?? 99;
                if (dist === 1) return "#FFA53B";
                if (dist === 2) return "#F5D547";
                return "#F5D547";
              }
              if (data.isDecoy) return "#FFA53B";
              return "#2A2A2E";
            },
            "shadow-blur": (ele: any) => {
              const data = ele.data();
              if (data.isRoot && highlightActive) return 32;
              if (data.isOnPath && highlightActive) return 12;
              return 0;
            },
            "shadow-color": (ele: any) => {
              const data = ele.data();
              if (data.isRoot && highlightActive) return "#E50914";
              if (data.isOnPath && highlightActive) {
                const dist = hopDistances[data.id] ?? 99;
                if (dist === 1) return "#FFA53B";
                if (dist === 2) return "#F5D547";
              }
              return "transparent";
            },
            "shadow-opacity": (ele: any) => {
              const data = ele.data();
              if (data.isRoot && highlightActive) return 0.5;
              if (data.isOnPath && highlightActive) return 0.3;
              return 0;
            },
          } as any,
        },
        {
          selector: "edge",
          style: {
            width: (ele: any) => (ele.data("isOnPath") && highlightActive ? 3 : 1),
            "line-style": (ele: any) => (ele.data("isOnPath") && highlightActive ? "dashed" : "solid"),
            "line-dash-pattern": [6, 4],
            opacity: (ele: any) => {
              const data = ele.data();
              if (!highlightActive) return 1.0;
              if (data.isOnPath) return 1.0;
              return data.isDimmed ? 0.3 : 0.15;
            },
            "line-color": (ele: any) => {
              if (ele.data("isOnPath") && highlightActive) {
                return "#E50914";
              }
              return "#FFFFFF";
            },
            "target-arrow-color": (ele: any) => (ele.data("isOnPath") && highlightActive ? "#E50914" : "#FFFFFF"),
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "shadow-blur": (ele: any) => (ele.data("isOnPath") && highlightActive ? 8 : 0),
            "shadow-color": (ele: any) => (ele.data("isOnPath") && highlightActive ? "#E50914" : "transparent"),
            "shadow-opacity": (ele: any) => (ele.data("isOnPath") && highlightActive ? 0.8 : 0),
          } as any,
        },
      ],
      userZoomingEnabled: true,
      userPanningEnabled: true,
    });


    // Fit graph viewport to use the full canvas space beautifully
    cy.fit(undefined, 30);

    // Lock zoom-out so the graph can never shrink into invisibility
    cy.minZoom(cy.zoom() * 0.8);
    cy.maxZoom(3);

    // Track root cause node position for HTML overlay pulse
    cy.on("render", () => {
      const rootNode = cy.getElementById(rootCauseId);
      if (rootNode && rootNode.length > 0) {
        setRootPos(rootNode.renderedPosition());
      }
    });

    // Marching ants animation loop for path edges
    let animationFrameId: number;
    let dashOffset = 0;
    const animateEdges = () => {
      dashOffset -= 0.5; // Flow speed
      cy.edges('[?isOnPath]').style('line-dash-offset', dashOffset);
      animationFrameId = requestAnimationFrame(animateEdges);
    };
    if (highlightActive) {
      animateEdges();
    }

    // Listen for node click events to trigger sidebar detail drawer
    cy.on("tap", "node", (evt) => {
      const node = evt.target;
      const data = node.data();
      onNodeClick?.(data.id, data.isCluster || false, data.tier || null);
    });

    cyRef.current = cy;

    return () => {
      cancelAnimationFrame(animationFrameId);
      if (cyRef.current) {
        try {
          let limit = 100;
          while ((cy as any).batching() && limit > 0) {
            cy.endBatch();
            limit--;
          }
          cy.destroy();
        } catch {
          // ignore
        }
        cyRef.current = null;
      }
    };
  }, [topology, incident, rootCauseId, pathNodes, highlightActive, expandedTiers, pathTiers, onNodeClick]);

  return (
    <div className="relative w-full h-full scanline-grid border border-border-muted">
      {/* NOC Header */}
      <div className="absolute top-3 left-3 z-10 font-mono text-[10px] text-grey-muted select-none flex items-center gap-2">
        <span className="inline-block w-1.5 h-1.5 bg-red-critical rounded-full animate-ping"></span>
        <span>TOPOLOGY_ENGINE // ROOT_CAUSE_SUSPECT: <span className="text-red-critical text-status-glow font-bold font-mono">{rootCauseId}</span></span>
      </div>

      {/* Cytoscape element */}
      <div ref={containerRef} className="w-full h-full animate-[fade-in_0.5s_ease-out]" />

      {/* Cinematic Pulsing Radar Ping Overlay for Root Cause */}
      {highlightActive && rootCauseId && rootPos.x !== -999 && (
        <div 
          className="absolute pointer-events-none rounded-full border border-[#E50914] animate-ping"
          style={{
            left: rootPos.x - 40,
            top: rootPos.y - 40,
            width: 80,
            height: 80,
            opacity: 0.8
          }}
        />
      )}

      {/* Legend */}
      <div className="absolute bottom-3 left-3 right-3 z-10 font-mono text-[9px] text-grey-muted flex flex-wrap gap-x-4 gap-y-1 bg-panel/90 backdrop-blur border border-border-muted px-2 py-1.5 rounded">
        <div className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 bg-red-critical"></span>
          <span>Root Cause</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 bg-[#E8A94B]"></span>
          <span>Causal Dependency</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 bg-[#1A1A1E] border border-border-muted rounded-sm"></span>
          <span>Collapsed Cluster</span>
        </div>
        <div className="flex items-center gap-2 border-l border-border-muted pl-2">
          <span>TIERS:</span>
          <span className="flex items-center gap-1"><span className="inline-block w-1.5 h-1.5 bg-[#1F1A2B]"></span>edge</span>
          <span className="flex items-center gap-1"><span className="inline-block w-1.5 h-1.5 bg-[#121A2E]"></span>net</span>
          <span className="flex items-center gap-1"><span className="inline-block w-1.5 h-1.5 bg-[#0E202B]"></span>web</span>
          <span className="flex items-center gap-1"><span className="inline-block w-1.5 h-1.5 bg-[#09241C]"></span>app</span>
          <span className="flex items-center gap-1"><span className="inline-block w-1.5 h-1.5 bg-[#0D201A]"></span>data</span>
        </div>
      </div>
    </div>
  );
}
