// Synthetic fusion-dev.dump accounts. Global setup grants each one its `grants` in the IAM.
export const PASSWORD = process.env.E2E_PASSWORD ?? "fusion123";

export interface Account {
  username: string;
  role: string;
  grants: readonly string[];
}

export const ACCOUNTS = {
  student: { username: "stu00001", role: "ug_student", grants: [] },
  placementOfficer: {
    username: "stf00062", role: "placement_officer", grants: ["placement_officer"],
  },
  cmsHandler: {
    username: "stf00063", role: "Complaint Handler", grants: ["Complaint Handler"],
  },
  cmsSupervisor: {
    username: "fac00001", role: "Complaint Supervisor", grants: ["Complaint Supervisor"],
  },
  cmsAdmin: {
    username: "stf00064", role: "adminstrator", grants: ["adminstrator"],
  },
} as const satisfies Record<string, Account>;

export type AccountKey = keyof typeof ACCOUNTS;
