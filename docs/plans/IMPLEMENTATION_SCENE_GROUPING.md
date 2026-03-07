# Scene Grouping and Filtering Implementation Plan

Implement functionality to group shots by scene and filter them by individual scenes using tabs in the Edit Session page.

## Proposed Changes

### Frontend Enhancements

#### [MODIFY] [types/index.ts](file:///c:/AI/ai_video_factory_v1/web_ui/frontend/src/types/index.ts)
- Add `scene_index?: number` to the `Shot` interface.

#### [MODIFY] [page.tsx](file:///c:/AI/ai_video_factory_v1/web_ui/frontend/src/app/sessions/%5Bid%5D/edit/page.tsx)
- Pass `session.story.scenes` to the `ShotGrid` component.

#### [MODIFY] [ShotGrid.tsx](file:///c:/AI/ai_video_factory_v1/web_ui/frontend/src/components/shots/ShotGrid.tsx)
- Add state for `isGroupingEnabled` and `activeSceneTab` (default "All").
- Add a "Group by Scene" toggle in the grid header.
- Implement scene tabs (All + individual scenes) appearing above the grid when grouping is enabled.
- Logic to group shots by `scene_index` and filter based on `activeSceneTab`.
- Render scene headers with details (Scene number, Location, Action) above each group.

## Verification
- Toggle grouping and verify headers/tabs appear.
- Select different scene tabs and ensure shots/headers are filtered correctly.
- Ensure existing "All Images"/"All Videos" toggles still work within the filtered view.
