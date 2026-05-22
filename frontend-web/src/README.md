# Frontend Web (React Dashboard)

This folder contains the React-based Web Dashboard for the Safe Mobility System.

## Prototype Implementation
Currently, the application is built as a **prototype**, with an aesthetic modern UI ready for integration with AWS and MongoDB. 

### Key Files and Descriptions:
*   `src/main.tsx`: Entry point for the React application.
*   `src/App.tsx`: Main routing component setup using `react-router-dom`.
*   `src/index.css`: Global design tokens (colors, variables) and base CSS styles ensuring a premium, dark-mode look.
*   `src/screens/Dashboard.tsx`: The primary dashboard screen.
    *   **Features:** Displays real-time device stats, a placeholder map for live device tracking (ready for AWS Location Services), Alerts Timeline & Riding Environment charts (using `recharts`), and a Device Log Management table.
    *   **Data:** Currently uses mocked data (`MOCK_STATS`, `MOCK_EVENTS`, `MOCK_CHART_DATA`) to simulate data fetched from an AWS-hosted API/MongoDB backend.
*   `src/screens/Dashboard.css`: Dedicated stylesheet for the Dashboard, applying CSS Grid/Flexbox layouts and hover/pulse animations for a dynamic feel.
*   `src/vite-env.d.ts`: TypeScript definitions for Vite.

## Future AWS & MongoDB Integration
When transitioning from the prototype to production:
1.  **MongoDB**: Replace the mock data arrays in `Dashboard.tsx` with asynchronous `fetch` calls to your FastAPI backend, which will query MongoDB collections (e.g., `events`, `devices`).
2.  **AWS**: Integrate AWS Location Services for the `Map` component and AWS Cognito for authentication.
