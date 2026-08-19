export type SafetyProcedure = {
  code: string;
  title: string;
  category: string;
  status: "Controlled" | "Draft review";
};

export const SAFETY_PROGRAM_URL =
  "https://docs.google.com/document/d/1ApKQs4xIR8axW0lIaeqqATDVaZWs1jvSzaZwYK6wUNw/edit?usp=drivesdk";

export const safetyProcedures: SafetyProcedure[] = [
  { code: "SWP-001", title: "Excavation and Trenching", category: "Earthworks", status: "Controlled" },
  { code: "SWP-002", title: "Ground Disturbance and Utility Locating", category: "Utilities", status: "Controlled" },
  { code: "SWP-003", title: "Mobile Equipment and Spotters", category: "Equipment", status: "Controlled" },
  { code: "SWP-004", title: "Traffic Control and Public Interface", category: "Roadwork", status: "Controlled" },
  { code: "SWP-005", title: "Confined Space Entry", category: "High Risk", status: "Draft review" },
  { code: "SWP-006", title: "Lockout and Energy Isolation", category: "High Risk", status: "Draft review" },
  { code: "SWP-007", title: "Silica Exposure Control", category: "Occupational Health", status: "Controlled" },
  { code: "SWP-008", title: "Lifting, Rigging and Suspended Loads", category: "Equipment", status: "Controlled" },
];

export const controlledSafetyProcedures = safetyProcedures.filter((procedure) => procedure.status === "Controlled");
