import { useEffect } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../src/context/AuthContext';

export default function RootIndex() {
  const { token, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    if (token) {
      router.replace('/(tabs)');
    } else {
      router.replace('/login');
    }
  }, [token, isLoading, router]);

  return (
    <View style={{ flex: 1, backgroundColor: '#0f172a', alignItems: 'center', justifyContent: 'center' }}>
      <ActivityIndicator size="large" color="#3b82f6" />
    </View>
  );
}
