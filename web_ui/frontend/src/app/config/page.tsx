/**
 * Global Configuration Page
 */
'use client';

import { useState, useEffect } from 'react';
import { useConfig, useUpdateConfig } from '@/hooks/useAgents';
import { Save, RefreshCw } from 'lucide-react';

export default function ConfigPage() {
  const { data: config, isLoading, error } = useConfig();
  const updateConfigMutation = useUpdateConfig();

  const [formData, setFormData] = useState({
    llm_provider: '',
    image_generation_mode: '',
    comfy_url: '',
    target_video_length: 0,
    gemini_api_key: '',
    openai_api_key: '',
    elevenlabs_api_key: '',
  });

  useEffect(() => {
    if (config) {
      setFormData({
        llm_provider: config.llm_provider || 'gemini',
        image_generation_mode: config.image_generation_mode || 'comfyui',
        comfy_url: config.comfy_url || 'http://127.0.0.1:8188',
        target_video_length: config.target_video_length || 600,
        gemini_api_key: '', // Don't populate sensitive keys from GET
        openai_api_key: '',
        elevenlabs_api_key: '',
      });
    }
  }, [config]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Only send non-empty keys
      const updates: any = { ...formData };
      if (!updates.gemini_api_key) delete updates.gemini_api_key;
      if (!updates.openai_api_key) delete updates.openai_api_key;
      if (!updates.elevenlabs_api_key) delete updates.elevenlabs_api_key;

      await updateConfigMutation.mutateAsync(updates);
      alert('Configuration updated successfully!');
    } catch (error) {
      console.error('Failed to update config:', error);
      alert('Failed to update configuration.');
    }
  };

  if (isLoading) {
    return <div className="container mx-auto px-4 py-8">Loading configuration...</div>;
  }

  if (error) {
    return <div className="container mx-auto px-4 py-8 text-red-500">Error loading configuration.</div>;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Global Configuration</h1>
        <p className="text-muted-foreground">
          System-wide settings for the AI Video Factory
        </p>
      </div>

      <form onSubmit={handleSubmit} className="max-w-2xl space-y-8">
        {/* Core Settings */}
        <section className="space-y-4">
          <h2 className="text-xl font-semibold border-b pb-2">Core Settings</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">LLM Provider</label>
              <select 
                value={formData.llm_provider}
                onChange={(e) => setFormData({...formData, llm_provider: e.target.value})}
                className="w-full border rounded-md p-2 text-sm"
              >
                <option value="gemini">Google Gemini</option>
                <option value="openai">OpenAI (ChatGPT)</option>
                <option value="ollama">Ollama (Local)</option>
                <option value="lmstudio">LM Studio (Local)</option>
                <option value="zhipu">Zhipu AI</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Image Mode</label>
              <select 
                value={formData.image_generation_mode}
                onChange={(e) => setFormData({...formData, image_generation_mode: e.target.value})}
                className="w-full border rounded-md p-2 text-sm"
              >
                <option value="comfyui">ComfyUI (Local)</option>
                <option value="gemini">Gemini (Cloud)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">ComfyUI URL</label>
            <input 
              type="text"
              value={formData.comfy_url}
              onChange={(e) => setFormData({...formData, comfy_url: e.target.value})}
              className="w-full border rounded-md p-2 text-sm"
              placeholder="http://127.0.0.1:8188"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Default Target Video Length (seconds)</label>
            <input 
              type="number"
              value={formData.target_video_length}
              onChange={(e) => setFormData({...formData, target_video_length: parseInt(e.target.value)})}
              className="w-full border rounded-md p-2 text-sm"
            />
          </div>
        </section>

        {/* API Keys */}
        <section className="space-y-4">
          <h2 className="text-xl font-semibold border-b pb-2">API Keys</h2>
          <p className="text-xs text-muted-foreground italic">
            Note: Keys are saved to the .env file. Leave blank to keep existing values.
          </p>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Gemini API Key</label>
              <input 
                type="password"
                value={formData.gemini_api_key}
                onChange={(e) => setFormData({...formData, gemini_api_key: e.target.value})}
                className="w-full border rounded-md p-2 text-sm"
                placeholder="Paste new key to update..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">OpenAI API Key</label>
              <input 
                type="password"
                value={formData.openai_api_key}
                onChange={(e) => setFormData({...formData, openai_api_key: e.target.value})}
                className="w-full border rounded-md p-2 text-sm"
                placeholder="Paste new key to update..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">ElevenLabs API Key</label>
              <input 
                type="password"
                value={formData.elevenlabs_api_key}
                onChange={(e) => setFormData({...formData, elevenlabs_api_key: e.target.value})}
                className="w-full border rounded-md p-2 text-sm"
                placeholder="Paste new key to update..."
              />
            </div>
          </div>
        </section>

        <div className="flex justify-end pt-4">
          <button
            type="submit"
            disabled={updateConfigMutation.isPending}
            className="px-6 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            {updateConfigMutation.isPending ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Configuration
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
