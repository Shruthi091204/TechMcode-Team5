"use client";

import React from "react";
import { TimelineEvent } from "../lib/types";
import {
  Settings,
  AlertTriangle,
  Zap,
  Terminal,
  ArrowDownRight,
  LucideIcon,
} from "lucide-react";

interface IncidentTimelineProps {
  events: TimelineEvent[];
  counterfactualActive?: boolean;
  counterfactualString?: string | null;
}

const kindIcons: Record<TimelineEvent["kind"], LucideIcon> = {
  config: Settings,
  alert: AlertTriangle,
  anomaly: Zap,
  log: Terminal,
  propagation: ArrowDownRight,
};

const kindColors: Record<TimelineEvent["kind"], string> = {
  config: "text-[#FFFFFF]",
  alert: "text-[#E8A94B]",
  anomaly: "text-[#FFFFFF]",
  log: "text-[#FFFFFF]",
  propagation: "text-[#FFFFFF]",
};

export default function IncidentTimeline({
  events,
  counterfactualActive = false,
  counterfactualString = null,
}: IncidentTimelineProps) {
  // Sort events by timestamp
  const sortedEvents = [...events].sort((a, b) => a.ts.localeCompare(b.ts));

  // Determine if an event is affected by the counterfactual
  // The counterfactual targets "config change on db-01" or the first config event
  const isEventAffected = (event: TimelineEvent) => {
    if (!counterfactualActive || !counterfactualString) return false;
    // Check if the event matches the target of the counterfactual
    // In our scenario, the counterfactual addresses the config change on db-01
    return event.kind === "config" && event.component_id === "db-01";
  };

  return (
    <div className="w-full bg-panel border border-border-muted/20 p-4 font-mono select-none">
      <div className="text-xs text-text-muted mb-3 flex items-center justify-between border-b border-border-muted/10 pb-2">
        <span>INCIDENT_TIMELINE // PROPAGATION_TRACE</span>
        <span>EVENTS: {sortedEvents.length}</span>
      </div>

      <div className="relative border-l border-border-muted/20 pl-4 ml-2 flex flex-col gap-4">
        {sortedEvents.map((event, index) => {
          const Icon = kindIcons[event.kind] || Terminal;
          const isAffected = isEventAffected(event);

          return (
            <div
              key={index}
              className={`relative flex items-start gap-3 transition-opacity duration-200 ${
                isAffected ? "opacity-40" : "opacity-100"
              }`}
            >
              {/* Timeline marker node */}
              <div className="absolute -left-[25px] bg-panel p-0.5 border border-border-muted/20">
                <Icon size={14} className={kindColors[event.kind]} />
              </div>

              {/* Event Content */}
              <div className="flex-1 min-w-0 grid grid-cols-1 sm:grid-cols-[100px_120px_1fr] gap-2 items-center text-xs">
                {/* Timestamp */}
                <div className="text-text-muted font-bold tabular-nums">
                  {event.ts}
                </div>

                {/* Component ID */}
                <div className="text-foreground/80 font-bold border-r border-border-muted/10 pr-2 overflow-hidden text-ellipsis whitespace-nowrap">
                  {event.component_id}
                </div>

                {/* Description */}
                <div
                  className={`text-foreground leading-relaxed ${
                    isAffected ? "line-through text-text-muted/60" : ""
                  }`}
                >
                  <span
                    className={`inline-block mr-2 px-1 text-[10px] border uppercase ${
                      event.kind === "config"
                        ? "border-[#918F90]/30 text-text-muted"
                        : event.kind === "anomaly"
                        ? "border-primary/30 text-primary"
                        : event.kind === "alert"
                        ? "border-correlated/30 text-correlated"
                        : "border-border-muted/10 text-foreground/70"
                    }`}
                  >
                    {event.kind}
                  </span>
                  {event.description}
                  {isAffected && (
                    <span className="text-[10px] font-bold text-confirmed ml-2 block sm:inline">
                      {"// STRIKE: COUNTERFACTUAL_REMOVED"}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
