import apiClient from './client';

export const testVisionModel = async (
    modelId: string,
    prompt: string,
    image: File,
    system_prompt?: string
): Promise<{ job_id: string; status: string }> => {
    const formData = new FormData();
    formData.append('model_id', modelId);
    formData.append('prompt', prompt);
    formData.append('image', image);
    if (system_prompt) {
        formData.append('system_prompt', system_prompt);
    }

    const response = await apiClient.post<{ job_id: string; status: string }>(
        '/llm-models/test-vision',
        formData,
        {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        }
    );
    return response.data;
};
