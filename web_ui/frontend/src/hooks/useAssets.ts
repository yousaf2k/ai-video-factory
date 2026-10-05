/**
 * React hooks for the asset library
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import type { GenerateAssetRequest } from '@/types';

export function useAssetLibraries() {
  return useQuery({
    queryKey: ['asset-libraries'],
    queryFn: () => api.listAssetLibraries(),
    staleTime: 30000,
  });
}

export function useUpdateAssetLibraries() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (paths: string[]) => api.updateAssetLibraries(paths),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['asset-libraries'] });
      queryClient.invalidateQueries({ queryKey: ['asset-tree'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
  });
}

export function useAssetTree(library?: string) {
  return useQuery({
    queryKey: ['asset-tree', library ?? 'default'],
    queryFn: () => api.getAssetTree(library),
    staleTime: 10000,
  });
}

export function useAssets(cat: string | null, library?: string) {
  return useQuery({
    queryKey: ['assets', library ?? 'default', cat],
    queryFn: () => api.listAssets(cat!, library),
    enabled: !!cat,
    staleTime: 10000,
  });
}

export function useAssetSearch(query: string, library?: string) {
  return useQuery({
    queryKey: ['asset-search', library ?? 'default', query],
    queryFn: () => api.searchAssets(query, library),
    enabled: query.trim().length > 0,
    staleTime: 10000,
  });
}

export function useAssetEntry(ref: string | null, probe: boolean = false) {
  return useQuery({
    queryKey: ['asset-entry', ref, probe],
    queryFn: () => api.getAssetEntry(ref!, probe),
    enabled: !!ref,
  });
}

function useInvalidateAssets() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ['assets'] });
    queryClient.invalidateQueries({ queryKey: ['asset-tree'] });
    queryClient.invalidateQueries({ queryKey: ['asset-search'] });
    queryClient.invalidateQueries({ queryKey: ['asset-entry'] });
  };
}

export function useUploadAssets() {
  const invalidate = useInvalidateAssets();
  return useMutation({
    mutationFn: ({ cat, files, library }: { cat: string; files: File[]; library?: string }) =>
      api.uploadAssets(cat, files, library),
    onSuccess: invalidate,
  });
}

export function useImportAsset() {
  const invalidate = useInvalidateAssets();
  return useMutation({
    mutationFn: ({ ref, cat, title, library }: { ref: string; cat: string; title?: string; library?: string }) =>
      api.importAsset(ref, cat, title, library),
    onSuccess: invalidate,
  });
}

export function useRenameAsset() {
  const invalidate = useInvalidateAssets();
  return useMutation({
    mutationFn: ({ ref, title }: { ref: string; title: string }) => api.renameAsset(ref, title),
    onSuccess: invalidate,
  });
}

export function useMoveAsset() {
  const invalidate = useInvalidateAssets();
  return useMutation({
    mutationFn: ({ ref, toCat }: { ref: string; toCat: string }) => api.moveAsset(ref, toCat),
    onSuccess: invalidate,
  });
}

export function useDeleteAsset() {
  const invalidate = useInvalidateAssets();
  return useMutation({
    mutationFn: ({ ref, force }: { ref: string; force?: boolean }) => api.deleteAsset(ref, force),
    onSuccess: invalidate,
  });
}

export function useCreateAssetCategory() {
  const invalidate = useInvalidateAssets();
  return useMutation({
    mutationFn: ({ cat, name, library }: { cat: string; name: string; library?: string }) =>
      api.createAssetCategory(cat, name, library),
    onSuccess: invalidate,
  });
}

export function useDeleteAssetCategory() {
  const invalidate = useInvalidateAssets();
  return useMutation({
    mutationFn: ({ cat, force, library }: { cat: string; force?: boolean; library?: string }) =>
      api.deleteAssetCategory(cat, force, library),
    onSuccess: invalidate,
  });
}

export function useMoveAssetCategory() {
  const invalidate = useInvalidateAssets();
  return useMutation({
    mutationFn: ({ cat, toParent, library }: { cat: string; toParent: string; library?: string }) =>
      api.moveAssetCategory(cat, toParent, library),
    onSuccess: invalidate,
  });
}

export function useRenameAssetCategory() {
  const invalidate = useInvalidateAssets();
  return useMutation({
    mutationFn: ({ cat, name, library }: { cat: string; name: string; library?: string }) =>
      api.renameAssetCategory(cat, name, library),
    onSuccess: invalidate,
  });
}

// --- Project asset pool + shot references ---------------------------------

function useInvalidateProject(projectId: string, shotId?: string | number) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ['project-assets', projectId] });
    queryClient.invalidateQueries({ queryKey: ['shot-refs', projectId] });
    queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
    queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    if (shotId !== undefined) {
      queryClient.invalidateQueries({ queryKey: ['shot-refs', projectId, shotId] });
    }
  };
}

export function useProjectAssets(projectId: string) {
  return useQuery({
    queryKey: ['project-assets', projectId],
    queryFn: () => api.getProjectAssets(projectId),
    enabled: !!projectId,
    staleTime: 5000,
  });
}

export function useAddProjectAssets(projectId: string) {
  const invalidate = useInvalidateProject(projectId);
  return useMutation({
    mutationFn: (refs: string[]) => api.addProjectAssets(projectId, refs),
    onSuccess: invalidate,
  });
}

export function useRemoveProjectAsset(projectId: string) {
  const invalidate = useInvalidateProject(projectId);
  return useMutation({
    mutationFn: ({ ref, strip }: { ref: string; strip?: boolean }) =>
      api.removeProjectAsset(projectId, ref, strip),
    onSuccess: invalidate,
  });
}

export function useShotReferences(projectId: string, shotId: string | number | null) {
  return useQuery({
    queryKey: ['shot-refs', projectId, shotId],
    queryFn: () => api.getShotReferences(projectId, shotId!),
    enabled: !!projectId && !!shotId,
  });
}

export function useAddShotReferences(projectId: string, shotId: string | number) {
  const invalidate = useInvalidateProject(projectId, shotId);
  return useMutation({
    mutationFn: (refs: string[]) => api.addShotReferences(projectId, shotId, refs),
    onSuccess: invalidate,
  });
}

export function useSetShotReferences(projectId: string, shotId: string | number) {
  const invalidate = useInvalidateProject(projectId, shotId);
  return useMutation({
    mutationFn: (refs: string[]) => api.setShotReferences(projectId, shotId, refs),
    onSuccess: invalidate,
  });
}

export function useRemoveShotReference(projectId: string, shotId: string | number) {
  const invalidate = useInvalidateProject(projectId, shotId);
  return useMutation({
    mutationFn: (ref: string) => api.removeShotReference(projectId, shotId, ref),
    onSuccess: invalidate,
  });
}

export function useReferenceAsSource(projectId: string, shotId: string | number) {
  const invalidate = useInvalidateProject(projectId, shotId);
  return useMutation({
    mutationFn: ({ ref, slot }: { ref: string; slot: 'then' | 'now' }) =>
      api.useReferenceAsSource(projectId, shotId, ref, slot),
    onSuccess: invalidate,
  });
}

export function useProjectMedia(projectId: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ['project-media', projectId],
    queryFn: () => api.getProjectMedia(projectId),
    enabled: !!projectId && enabled,
    staleTime: 10000,
  });
}

// ---------------------------------------------------------------------------
// Guides (text) content + generation into the library
// ---------------------------------------------------------------------------

export function useAssetText(ref: string | null, enabled: boolean = true) {
  return useQuery({
    queryKey: ['asset-text', ref],
    queryFn: () => api.getAssetText(ref!),
    enabled: !!ref && enabled,
    staleTime: 60000,
  });
}

export function useGenerateOptions() {
  return useQuery({
    queryKey: ['asset-generate-options'],
    queryFn: () => api.getGenerateOptions(),
    staleTime: 60000,
  });
}

export function useAssetGenerations() {
  return useQuery({
    queryKey: ['asset-generations'],
    queryFn: () => api.listAssetGenerations(),
    refetchInterval: (query) =>
      query.state.data?.some((g) => g.status === 'queued' || g.status === 'running') ? 3000 : false,
  });
}

export function useAssetGeneration(genId: string | null) {
  return useQuery({
    queryKey: ['asset-generation', genId],
    queryFn: () => api.getAssetGeneration(genId!),
    enabled: !!genId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'queued' || status === 'running' ? 1500 : false;
    },
  });
}

export function useStartGeneration() {
  return useMutation({
    mutationFn: (request: GenerateAssetRequest) => api.startAssetGeneration(request),
  });
}

export function useCancelGeneration() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (genId: string) => api.cancelAssetGeneration(genId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['asset-generations'] });
      queryClient.invalidateQueries({ queryKey: ['asset-generation'] });
    },
  });
}
