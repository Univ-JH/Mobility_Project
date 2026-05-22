import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/layout/Layout';
import { Dashboard } from './screens/Dashboard';
import { LiveMap } from './screens/LiveMap';
import { EventLogs } from './screens/EventLogs';

import { Policies } from './screens/Policies';
import { Emergencies } from './screens/Emergencies';

// Create a client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="map" element={<LiveMap />} />
            <Route path="logs" element={<EventLogs />} />
            <Route path="policies" element={<Policies />} />
            <Route path="emergencies" element={<Emergencies />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </Router>
    </QueryClientProvider>
  );
};

export default App;
