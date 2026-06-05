import { Stack } from 'expo-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StatusBar } from 'expo-status-bar';
import { AuthProvider } from '../src/context/AuthContext';
import { EmergencyProvider } from '../src/context/EmergencyContext';
import { GlobalEmergencyOverlay } from '../src/components/GlobalEmergencyOverlay';

const queryClient = new QueryClient();

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <EmergencyProvider>
          <StatusBar style="light" />
          <Stack>
            <Stack.Screen name="index" options={{ headerShown: false }} />
            <Stack.Screen name="login" options={{ headerShown: false }} />
            <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
            <Stack.Screen name="riding/[deviceId]" options={{ headerShown: false }} />
            <Stack.Screen name="pair" options={{ presentation: 'modal', title: 'Pair Device' }} />
          </Stack>
          <GlobalEmergencyOverlay />
        </EmergencyProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
