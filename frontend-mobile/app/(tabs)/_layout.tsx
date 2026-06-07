import { Tabs, Redirect } from 'expo-router';
import { View, ActivityIndicator } from 'react-native';
import { Home, List, User, Cpu } from 'lucide-react-native';
import { useAuth } from '../../src/context/AuthContext';
import { useEmergencyPolling } from '../../src/hooks/useEmergencyPolling';

export default function TabLayout() {
  const { token, isLoading } = useAuth();
  useEmergencyPolling();

  if (isLoading) {
    return (
      <View style={{ flex: 1, backgroundColor: '#0f172a', alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator size="large" color="#3b82f6" />
      </View>
    );
  }
  if (!token) return <Redirect href="/login" />;

  return (
    <Tabs screenOptions={{
      tabBarActiveTintColor: '#3b82f6',
      tabBarInactiveTintColor: '#64748b',
      tabBarStyle: { backgroundColor: '#0f172a', borderTopColor: '#1e293b' },
      headerShown: false,
    }}>
      <Tabs.Screen
        name="index"
        options={{ title: '홈', tabBarIcon: ({ color }) => <Home color={color} size={24} /> }}
      />
      <Tabs.Screen
        name="devices"
        options={{ title: '디바이스', tabBarIcon: ({ color }) => <Cpu color={color} size={24} /> }}
      />
      <Tabs.Screen
        name="history"
        options={{ title: '주행기록', tabBarIcon: ({ color }) => <List color={color} size={24} /> }}
      />
      <Tabs.Screen
        name="profile"
        options={{ title: '프로필', tabBarIcon: ({ color }) => <User color={color} size={24} /> }}
      />
      <Tabs.Screen name="dashboard" options={{ href: null }} />
    </Tabs>
  );
}
