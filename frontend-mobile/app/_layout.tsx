import { Stack } from 'expo-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StatusBar } from 'expo-status-bar';
import { EmergencyProvider } from '../src/context/EmergencyContext';
import { GlobalEmergencyOverlay } from '../src/components/GlobalEmergencyOverlay';

const queryClient = new QueryClient();

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <EmergencyProvider>
        <StatusBar style="dark" />
        <Stack>
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen name="pair" options={{ presentation: 'modal', title: 'Pair Device' }} />
        </Stack>
        {/* Renders above all screens — AGENTS.md rule 2 compliance */}
        <GlobalEmergencyOverlay />
      </EmergencyProvider>
    </QueryClientProvider>
  );
}
