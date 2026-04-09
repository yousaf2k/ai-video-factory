import { EditorLayout } from '@/components/editor/EditorLayout';

export default function ProjectEditorPage({ params }: { params: { projectId: string } }) {
  return <EditorLayout projectId={params.projectId} />;
}
