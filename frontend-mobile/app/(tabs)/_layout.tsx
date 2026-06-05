import { Tabs } from 'expo-router';
import { Home, List, User } from 'lucide-react-native';
import { useEmergencyPolling } from '../../src/hooks/useEmergencyPolling';

export default function TabLayout() {
  // Polls /emergencies while app is in foreground; triggers GlobalEmergencyOverlay on new server emergency
  useEmergencyPolling();

  return (
    <Tabs screenOptions={{
      tabBarActiveTintColor: '#3b82f6',
      tabBarInactiveTintColor: '#94a3b8',
      headerShown: true,
      headerTitleStyle: { fontWeight: 'bold' }
    }}>
      <Tabs.Screen 
        name="index" 
        options={{
          title: 'Ride',
          tabBarIcon: ({ color }) => <Home color={color} size={24} />
        }} 
      />
      <Tabs.Screen 
        name="history" 
        options={{
          title: 'History',
          tabBarIcon: ({ color }) => <List color={color} size={24} />
        }} 
      />
      <Tabs.Screen 
        name="profile" 
        options={{
          title: 'Profile',
          tabBarIcon: ({ color }) => <User color={color} size={24} />
        }} 
      />
    </Tabs>
  );
}
