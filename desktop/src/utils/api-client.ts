import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosError } from 'axios';

const API_BASE_URL = 'http://localhost:8000';
const HEALTH_CHECK_ENDPOINT = '/health';
const MAX_RETRIES = 3;
const INITIAL_RETRY_DELAY = 1000;
const MAX_RETRY_DELAY = 10000;

interface HealthCheckResponse {
  status: string;
  version: string;
  mode: string;
  vault: boolean;
  llamaindex: boolean;
  websockets_enabled: boolean;
  ui_enabled: boolean;
}

class ApiClient {
  private client: AxiosInstance;
  private isBackendReady = false;
  private healthCheckPromise: Promise<boolean> | null = null;
  private healthCheckInterval: NodeJS.Timeout | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
    this.startHealthCheck();
  }

  private setupInterceptors(): void {
    this.client.interceptors.request.use(
      async (config) => {
        if (config.url !== HEALTH_CHECK_ENDPOINT) {
          await this.ensureBackendReady();
        }
        return config;
      },
      (error: Error) => Promise.reject(error)
    );

    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const config = error.config as AxiosRequestConfig & { _retryCount?: number };

        if (this.isConnectionError(error) && config && config.url !== HEALTH_CHECK_ENDPOINT) {
          config._retryCount = config._retryCount ?? 0;

          if (config._retryCount < MAX_RETRIES) {
            config._retryCount++;
            const delay = Math.min(
              INITIAL_RETRY_DELAY * Math.pow(2, config._retryCount - 1),
              MAX_RETRY_DELAY
            );

            await this.sleep(delay);

            this.isBackendReady = false;
            await this.ensureBackendReady();

            return this.client.request(config);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  private isConnectionError(error: AxiosError): boolean {
    return (
      !error.response &&
      (error.code === 'ECONNREFUSED' ||
        error.code === 'ENOTFOUND' ||
        error.code === 'ETIMEDOUT' ||
        error.message.includes('Network Error') ||
        error.message.includes('ERR_CONNECTION_REFUSED'))
    );
  }

  private async checkHealth(): Promise<boolean> {
    try {
      const response = await axios.get<HealthCheckResponse>(
        `${API_BASE_URL}${HEALTH_CHECK_ENDPOINT}`,
        {
          timeout: 5000,
          validateStatus: () => true,
        }
      );

      return response.status === 200 && response.data.status === 'healthy';
    } catch (_error) {
      return false;
    }
  }

  private async ensureBackendReady(): Promise<void> {
    if (this.isBackendReady) {
      return;
    }

    if (this.healthCheckPromise) {
      await this.healthCheckPromise;
      return;
    }

    this.healthCheckPromise = this.waitForBackend();
    await this.healthCheckPromise;
    this.healthCheckPromise = null;
  }

  private async waitForBackend(): Promise<boolean> {
    let attempts = 0;
    const maxAttempts = 10;

    while (attempts < maxAttempts) {
      const isHealthy = await this.checkHealth();

      if (isHealthy) {
        this.isBackendReady = true;
        return true;
      }

      attempts++;
      const delay = Math.min(INITIAL_RETRY_DELAY * Math.pow(2, attempts - 1), MAX_RETRY_DELAY);
      await this.sleep(delay);
    }

    throw new Error('Backend is not available after multiple attempts');
  }

  private startHealthCheck(): void {
    void this.checkHealth().then((isHealthy) => {
      this.isBackendReady = isHealthy;
    });

    this.healthCheckInterval = setInterval(() => {
      if (!this.isBackendReady) {
        void this.checkHealth().then((isHealthy) => {
          this.isBackendReady = isHealthy;
        });
      }
    }, 5000);
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  public async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  public async post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  public async put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  public async patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.patch<T>(url, data, config);
    return response.data;
  }

  public async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }

  public getBaseURL(): string {
    return API_BASE_URL;
  }

  public isReady(): boolean {
    return this.isBackendReady;
  }

  public cleanup(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }
  }
}

export const apiClient = new ApiClient();
export default apiClient;
