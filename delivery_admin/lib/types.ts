export type AdminSystemStatus = {
  database: {
    label: string;
    detail: string;
    warning?: string | null;
    persistent?: boolean;
  };
  photoStorage: {
    label: string;
    detail: string;
  };
};

export type DeliveryLocation = {
  id: string;
  name: string;
  customerCount?: number | null;
};

export type DeliveryReport = {
  id: number;
  clientSubmissionId: string;
  lineUserId: string;
  userName: string;
  customerId: string;
  customerName: string;
  locationId: string;
  locationName: string;
  photoObjectKey: string;
  photoUrl: string;
  latitude: number | null;
  longitude: number | null;
  accuracyM: number | null;
  capturedAtClient: string | null;
  receivedAtServer: string | null;
};

export type ReportsCursor = {
  beforeReceivedAt: string | null;
  beforeId: string;
};

export type ReportsResponse = {
  reports: DeliveryReport[];
  hasMore: boolean;
  nextCursor: ReportsCursor | null;
};

export type DeliveryUserAccess = {
  lineUserId: string;
  displayName: string;
  status: string;
  accessMode: "all" | "assigned";
  allowedLocationIds: string[];
  lastLoginAt: string | null;
};
