import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8401';
let accessTokenProvider: null | (() => Promise<string | null>) = null;

const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
});

type ApiMeta = {
  request_id?: string;
  total?: number;
  limit?: number;
  offset?: number;
};

type ApiEnvelope<T> = {
  data: T;
  meta: ApiMeta;
};

export type Principal = {
  user_id?: string | null;
  email: string;
  role: string;
  auth_mode: string;
};

export type AuthConfig = {
  auth_mode: string;
  interactive_login: boolean;
  provider?: string | null;
};

export const setAccessTokenProvider = (provider: null | (() => Promise<string | null>)) => {
  accessTokenProvider = provider;
};

const unwrapData = <T>(payload: any): T => {
  if (payload && typeof payload === 'object' && 'data' in payload && 'meta' in payload) {
    return payload.data as T;
  }
  return payload as T;
};

const unwrapEnvelope = <T>(payload: any): ApiEnvelope<T> => {
  if (payload && typeof payload === 'object' && 'data' in payload && 'meta' in payload) {
    return payload as ApiEnvelope<T>;
  }
  return {
    data: payload as T,
    meta: {},
  };
};

api.interceptors.request.use(async (config) => {
  if (!config.headers?.Authorization && accessTokenProvider) {
    const token = await accessTokenProvider();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

api.interceptors.response.use((response) => {
  const requestId = response.headers['x-request-id'];
  if (requestId && response.data && typeof response.data === 'object' && 'meta' in response.data) {
    response.data.meta = { ...response.data.meta, request_id: response.data.meta?.request_id || requestId };
  }
  return response;
});

// Applications
export const getApplications = async (): Promise<any[]> => {
  const res = await api.get('/applications/');
  return unwrapData<any[]>(res.data);
};

export const getApplicationsPage = async (params?: {
  q?: string;
  status?: string;
  offset?: number;
  limit?: number;
}): Promise<ApiEnvelope<any[]>> => {
  const res = await api.get('/applications/', { params });
  return unwrapEnvelope<any[]>(res.data);
};

export const getApplication = async (id: string): Promise<any> => {
  const res = await api.get(`/applications/${id}`);
  return unwrapData<any>(res.data);
};

export const createApplication = async (data: any) => {
  const res = await api.post('/applications/', data);
  return unwrapData(res.data);
};

export const updateApplication = async (id: string, data: any) => {
  const res = await api.put(`/applications/${id}`, data);
  return unwrapData(res.data);
};

export const deleteApplication = async (id: string) => {
  const res = await api.delete(`/applications/${id}`);
  return unwrapData(res.data);
};

// Databases
export const getDatabases = async (applicationId?: string): Promise<any[]> => {
  const params = applicationId ? { application_id: applicationId } : {};
  const res = await api.get('/databases/', { params });
  return unwrapData<any[]>(res.data);
};

export const getDatabasesPage = async (params?: {
  application_id?: string;
  q?: string;
  environment?: string;
  status?: string;
  offset?: number;
  limit?: number;
}): Promise<ApiEnvelope<any[]>> => {
  const res = await api.get('/databases/', { params });
  return unwrapEnvelope<any[]>(res.data);
};

export const getDatabase = async (id: string): Promise<any> => {
  const res = await api.get(`/databases/${id}`);
  return unwrapData<any>(res.data);
};

export const createDatabase = async (data: any) => {
  const res = await api.post('/databases/', data);
  return unwrapData(res.data);
};

export const updateDatabase = async (id: string, data: any) => {
  const res = await api.put(`/databases/${id}`, data);
  return unwrapData(res.data);
};

export const deleteDatabase = async (id: string) => {
  const res = await api.delete(`/databases/${id}`);
  return unwrapData(res.data);
};

// Database Instances
export const getDatabaseInstances = async (): Promise<any[]> => {
  const res = await api.get('/database-instances/');
  return unwrapData<any[]>(res.data);
};

export const getDatabaseInstancesPage = async (params?: {
  database_id?: string;
  q?: string;
  role?: string;
  status?: string;
  offset?: number;
  limit?: number;
}): Promise<ApiEnvelope<any[]>> => {
  const res = await api.get('/database-instances/', { params });
  return unwrapEnvelope<any[]>(res.data);
};

export const createDatabaseInstance = async (data: any) => {
  const res = await api.post('/database-instances/', data);
  return unwrapData(res.data);
};

export const updateDatabaseInstance = async (id: string, data: any) => {
  const res = await api.put(`/database-instances/${id}`, data);
  return unwrapData(res.data);
};

export const deleteDatabaseInstance = async (id: string) => {
  const res = await api.delete(`/database-instances/${id}`);
  return unwrapData(res.data);
};

export const testDatabaseConnection = async (data: any) => {
  // If instance_id is provided (editing mode with no password), use stored credentials
  if (data.instance_id && !data.password) {
    const res = await api.post(`/database-instances/${data.instance_id}/test-connection`);
    return res.data;
  }
  // Otherwise test with provided credentials
  const { instance_id, ...connectionData } = data;
  const res = await api.post('/database-instances/test-connection', connectionData);
  return res.data;
};

// Data Sources (Database Inventory)
export const getSourceTables = async (databaseId: string) => {
  const res = await api.get('/data-sources/tables', { params: { database_id: databaseId } });
  return unwrapData<any[]>(res.data);
};

export const getSourceTablesPage = async (params: {
  database_id: string;
  q?: string;
  schema_name?: string;
  offset?: number;
  limit?: number;
}): Promise<ApiEnvelope<any[]>> => {
  const res = await api.get('/data-sources/tables', { params });
  return unwrapEnvelope<any[]>(res.data);
};

export const extractSourceTables = async (data: { database_id: string; instance_id: string; schema?: string }) => {
  const res = await api.post('/data-sources/tables/extract', data);
  return unwrapData<any[]>(res.data);
};

export const extractSourceTableDetails = async (data: { instance_id: string; table_ids: string[] }) => {
  const res = await api.post('/data-sources/tables/extract-details', data);
  return unwrapData<any>(res.data);
};

export const getSourceTableDetails = async (tableId: string) => {
  const res = await api.get(`/data-sources/tables/${tableId}`);
  return unwrapData<any>(res.data);
};

export const provisionSharePointList = async (data: any) => {
  const res = await api.post('/provisioning/list', data);
  return unwrapData<any>(res.data);
};

export const getConnections = async (): Promise<any[]> => {
  const res = await api.get('/sharepoint-connections/');
  return unwrapData<any[]>(res.data);
};

export const getConnectionsPage = async (params?: {
  q?: string;
  status?: string;
  offset?: number;
  limit?: number;
}): Promise<ApiEnvelope<any[]>> => {
  const res = await api.get('/sharepoint-connections/', { params });
  return unwrapEnvelope<any[]>(res.data);
};

export const createConnection = async (data: any): Promise<any> => {
  const res = await api.post('/sharepoint-connections/', data);
  return unwrapData<any>(res.data);
};

export const updateConnection = async (id: string, data: any): Promise<any> => {
  const res = await api.put(`/sharepoint-connections/${id}`, data);
  return unwrapData<any>(res.data);
};

// Data Targets (SharePoint Inventory)
export const getSharePointSites = async (connectionId?: string) => {
  const res = await api.get('/data-targets/sites', {
    params: connectionId ? { connection_id: connectionId } : {}
  });
  return unwrapData<any[]>(res.data);
};

export const getSharePointSitesPage = async (params?: {
  connection_id?: string;
  q?: string;
  status?: string;
  offset?: number;
  limit?: number;
}): Promise<ApiEnvelope<any[]>> => {
  const res = await api.get('/data-targets/sites', { params });
  return unwrapEnvelope<any[]>(res.data);
};

export const extractSharePointSites = async (connectionId: string, query: string = "*") => {
  const res = await api.post('/data-targets/sites/extract', null, {
    params: { connection_id: connectionId, query }
  });
  return unwrapData<any[]>(res.data);
};

export const resolveSharePointSite = async (data: { connection_id: string; hostname: string; site_path: string }) => {
  const res = await api.post('/data-targets/sites/resolve', data);
  return unwrapData<any>(res.data);
};

export const getSharePointLists = async (siteId: string) => {
  const res = await api.get(`/data-targets/sites/${siteId}/lists`);
  return unwrapData<any[]>(res.data);
};

export const getSharePointListsPage = async (siteId: string, params?: {
  q?: string;
  is_provisioned?: boolean;
  offset?: number;
  limit?: number;
}): Promise<ApiEnvelope<any[]>> => {
  const res = await api.get(`/data-targets/sites/${siteId}/lists`, { params });
  return unwrapEnvelope<any[]>(res.data);
};

export const extractSharePointLists = async (siteId: string) => {
  const res = await api.post(`/data-targets/sites/${siteId}/lists/extract`);
  return unwrapData<any[]>(res.data);
};

export const getSharePointListsBySourceTable = async (tableId: string) => {
  const res = await api.get('/data-targets/lists/by-source', {
    params: { source_table_id: tableId }
  });
  return unwrapData<any[]>(res.data);
};

export const getSharePointColumns = async (listId: string) => {
  const res = await api.get(`/data-targets/lists/${listId}/columns`);
  return unwrapData<any[]>(res.data);
};

export const getSharePointColumnsPage = async (listId: string, params?: {
  q?: string;
  is_readonly?: boolean;
  offset?: number;
  limit?: number;
}): Promise<ApiEnvelope<any[]>> => {
  const res = await api.get(`/data-targets/lists/${listId}/columns`, { params });
  return unwrapEnvelope<any[]>(res.data);
};

export const extractSharePointColumns = async (listId: string) => {
  const res = await api.post(`/data-targets/lists/${listId}/columns/extract`);
  return unwrapData<any[]>(res.data);
};

export const getSyncDefinitions = async (): Promise<any[]> => {
  const res = await api.get('/sync-definitions/');
  return unwrapData<any[]>(res.data);
};

export const getSyncDefinitionsPage = async (params?: {
  q?: string;
  sync_mode?: string;
  is_paused?: boolean;
  offset?: number;
  limit?: number;
}): Promise<ApiEnvelope<any[]>> => {
  const res = await api.get('/sync-definitions/', { params });
  return unwrapEnvelope<any[]>(res.data);
};

export const getSyncDefinition = async (id: string): Promise<any> => {
  const res = await api.get(`/sync-definitions/${id}`);
  return unwrapData<any>(res.data);
};

export const createSyncDefinition = async (data: any): Promise<any> => {
  const res = await api.post('/sync-definitions/', data);
  return unwrapData<any>(res.data);
};

export const updateSyncDefinition = async (id: string, data: any): Promise<any> => {
  const res = await api.put(`/sync-definitions/${id}`, data);
  return unwrapData<any>(res.data);
};

export const deleteSyncDefinition = async (id: string): Promise<any> => {
  const res = await api.delete(`/sync-definitions/${id}`);
  return unwrapData<any>(res.data);
};

// Field Mappings
export const getFieldMappings = async (syncDefId: string): Promise<any[]> => {
  const res = await api.get(`/field-mappings/sync-definition/${syncDefId}`);
  return unwrapData<any[]>(res.data);
};

export const createFieldMapping = async (syncDefId: string, data: any): Promise<any> => {
  const res = await api.post(`/field-mappings/?sync_def_id=${syncDefId}`, data);
  return unwrapData<any>(res.data);
};

export const updateFieldMapping = async (mappingId: string, data: any): Promise<any> => {
  const res = await api.put(`/field-mappings/${mappingId}`, data);
  return unwrapData<any>(res.data);
};

export const deleteFieldMapping = async (mappingId: string): Promise<any> => {
  const res = await api.delete(`/field-mappings/${mappingId}`);
  return unwrapData<any>(res.data);
};

export const bulkUpdateFieldMappings = async (syncDefId: string, mappings: any[]): Promise<any[]> => {
  const res = await api.post(`/field-mappings/sync-definition/${syncDefId}/bulk`, mappings);
  return unwrapData<any[]>(res.data);
};

export const generateDriftReport = async (data: { sync_def_id: string, check_type: string }) => {
  const res = await api.post('/ops/drift-report', data);
  return unwrapData<any>(res.data);
};

export const triggerFailover = async (data: { new_primary_instance_id: string, old_primary_instance_id?: string }) => {
  const res = await api.post('/ops/failover', data);
  return unwrapData<any>(res.data);
};

export const triggerSync = async (syncDefId: string) => {
  const res = await api.post(`/ops/sync/${syncDefId}`);
  return unwrapData<any>(res.data);
};

export const resetSyncCursors = async (syncDefId: string) => {
  const res = await api.delete(`/ops/sync/${syncDefId}/cursors`);
  return unwrapData<any>(res.data);
};

export const getCurrentUser = async (): Promise<any> => {
  const res = await api.get('/auth/me');
  return unwrapData<any>(res.data);
};

export const getAuthConfig = async (): Promise<AuthConfig> => {
  const res = await api.get('/auth/config');
  return unwrapData<AuthConfig>(res.data);
};

export const getSyncRuns = async () => {
  const res = await api.get('/runs/');
  return unwrapData<any[]>(res.data);
};

export const getSyncRunsPage = async (params?: {
  sync_def_id?: string;
  status?: string;
  run_type?: string;
  offset?: number;
  limit?: number;
}): Promise<ApiEnvelope<any[]>> => {
  const res = await api.get('/runs/', { params });
  return unwrapEnvelope<any[]>(res.data);
};

// Schedules
export interface ScheduleInput {
  schedule_type: 'INTERVAL' | 'CRON';
  interval_seconds?: number;
  cron_expression?: string;
  timezone?: string;
}

export const previewSchedule = async (config: ScheduleInput): Promise<string[]> => {
  const res = await api.post('/schedules/preview', config);
  return res.data;
};

export const enableSchedule = async (syncDefId: string, config: ScheduleInput) => {
  const res = await api.post(`/schedules/${syncDefId}/enable`, config);
  return res.data;
};

export const disableSchedule = async (syncDefId: string) => {
  const res = await api.post(`/schedules/${syncDefId}/disable`);
  return res.data;
};

export const deleteSchedule = async (syncDefId: string) => {
  const res = await api.delete(`/schedules/${syncDefId}`);
  return res.data;
};

export const getScheduleAudit = async (syncDefId: string, limit: number = 50) => {
  const res = await api.get(`/schedules/${syncDefId}/audit`, { params: { limit } });
  return unwrapData<any[]>(res.data);
};

// CDC (placeholder - will be implemented in Epic 5)
export const enableCDC = async (syncDefId: string) => {
  const res = await api.post(`/cdc/${syncDefId}/enable-cdc`);
  return res.data;
};

export const disableCDC = async (syncDefId: string) => {
  const res = await api.post(`/cdc/${syncDefId}/disable-cdc`);
  return res.data;
};

// Replication Slots
export const getReplicationSlots = async (instanceId: string) => {
  const res = await api.get(`/replication/slots/${instanceId}`);
  return unwrapData<any[]>(res.data);
};

export const createReplicationSlot = async (instanceId: string, slotName: string, plugin: string = 'pgoutput') => {
  const res = await api.post('/replication/slots', {
    instance_id: instanceId,
    slot_name: slotName,
    plugin
  });
  return unwrapData<any>(res.data);
};

export const dropReplicationSlot = async (instanceId: string, slotName: string) => {
  const res = await api.delete('/replication/slots', {
    data: {
      instance_id: instanceId,
      slot_name: slotName
    }
  });
  return unwrapData<any>(res.data);
};

// Publications
export const getPublicationStatus = async (instanceId: string, pubName: string = "arcore_cdc_pub") => {
  const res = await api.get(`/replication/publications/${instanceId}`, { params: { pub_name: pubName } });
  return unwrapData<any>(res.data);
};

export const getPublicationAvailableTables = async (instanceId: string, schema: string = "public") => {
  const res = await api.get(`/replication/publications/${instanceId}/tables`, { params: { schema } });
  return unwrapData<any[]>(res.data);
};

export const createPublication = async (instanceId: string, pubName: string = "arcore_cdc_pub", forAllTables: boolean = true, tables: string[] = []) => {
  const res = await api.post('/replication/publications', {
    instance_id: instanceId,
    pub_name: pubName,
    for_all_tables: forAllTables,
    tables
  });
  return unwrapData<any>(res.data);
};

export const dropPublication = async (instanceId: string, pubName: string = "arcore_cdc_pub") => {
  const res = await api.delete('/replication/publications', {
    data: {
      instance_id: instanceId,
      pub_name: pubName
    }
  });
  return unwrapData<any>(res.data);
};

// Health Monitoring
export const getCdcHealth = async () => {
  const res = await api.get('/health/cdc-health');
  return unwrapData<any>(res.data);
};

export const getDatabaseStats = async () => {
  const res = await api.get('/health/database-stats');
  return unwrapData<any>(res.data);
};

export const dropHealthReplicationSlot = async (data: {
  slot_name: string;
  force?: boolean;
  instance_id?: string;
}) => {
  const res = await api.post('/health/drop-slot', data);
  return unwrapData<any>(res.data);
};

export const vacuumHealthTable = async (data: {
  schema: string;
  table: string;
  full?: boolean;
}) => {
  const res = await api.post('/health/vacuum-table', data);
  return unwrapData<any>(res.data);
};

// Metrics
export const getSystemCounts = async () => {
  const res = await api.get('/metrics/counts');
  return unwrapData<any>(res.data);
};

export const getSystemSnapshot = async (durationSeconds: number = 15) => {
  const res = await api.post('/metrics/system-snapshot', null, {
    params: { duration_seconds: durationSeconds }
  });
  return unwrapData<any>(res.data);
};

// Drift Metrics
export const getDriftSummary = async () => {
  const res = await api.get('/metrics/drift-summary');
  return unwrapData<any>(res.data);
};

export const getDriftMetrics = async () => {
  const res = await api.get('/metrics/drift-metrics');
  return unwrapData<any[]>(res.data);
};

export const triggerDriftReconciliation = async () => {
  const res = await api.post('/metrics/reconcile-drift');
  return unwrapData<any>(res.data);
};

export const getAuditLog = async (params?: {
  actor_email?: string;
  action?: string;
  resource_type?: string;
  resource_id?: string;
  offset?: number;
  limit?: number;
}) => {
  const res = await api.get('/audit/', { params });
  return unwrapEnvelope<any[]>(res.data);
};

export const getManagedUsers = async (params?: {
  email?: string;
  role?: string;
  status?: string;
  offset?: number;
  limit?: number;
}) => {
  const res = await api.get('/auth/users', { params });
  return unwrapEnvelope<any[]>(res.data);
};

export const updateManagedUser = async (userId: string, data: { email?: string; display_name?: string; role?: string; status?: string }) => {
  const res = await api.patch(`/auth/users/${userId}`, data);
  return unwrapData<any>(res.data);
};

export default api;
