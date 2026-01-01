import apiClient from './client';

export interface LLMModel {
    id: string;
    name: string;
    provider: string;
    api_base?: string;
    description?: string;
    is_default: boolean;
    config: Record<string, any>;
}

// Interface for discovered Ollama models (simplified from backend response)
export interface OllamaModel {
    name: string;
    model: string; // The model identifier used by Ollama
    modified_at: string;
    size: number;
    digest: string;
    details: Record<string, any>;
}

export interface LLMModelCreate {
    name: string;
    provider: string;
    api_key?: string;
    api_base?: string;
    description?: string;
    is_default?: boolean;
    config?: Record<string, any>;
}

export type LLMModelUpdate = Partial<LLMModelCreate>;


export const getModels = async (): Promise<LLMModel[]> => {
    const response = await apiClient.get<LLMModel[]>('/llm-models');
    return response.data;
};

export const createModel = async (data: LLMModelCreate): Promise<LLMModel> => {
    const response = await apiClient.post<LLMModel>('/llm-models', data);
    return response.data;
};

export const updateModel = async (id: string, data: LLMModelUpdate): Promise<LLMModel> => {
    const response = await apiClient.put<LLMModel>(`/llm-models/${id}`, data);
    return response.data;
};

export const deleteModel = async (id: string): Promise<void> => {
    await apiClient.delete(`/llm-models/${id}`);
};

export const discoverOllamaModels = async (): Promise<OllamaModel[]> => {
    const response = await apiClient.get<OllamaModel[]>('/llm-models/discover-ollama');
    return response.data;
};

export const testLLMModel = async (modelId: string, prompt: string, system_prompt?: string): Promise<string> => {
    const response = await apiClient.post<string>('/llm-models/test', { model_id: modelId, prompt, system_prompt });
    return response.data;
};
