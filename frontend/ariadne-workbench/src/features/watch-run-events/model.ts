import type { AssignmentEvent } from "../../shared/api/types";

export type WatchRunEventsState = {
  status: "idle" | "watching" | "blocked";
  events: AssignmentEvent[];
};
