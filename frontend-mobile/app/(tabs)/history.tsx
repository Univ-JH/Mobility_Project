import React from 'react';
import { View, Text, StyleSheet, FlatList, ActivityIndicator } from 'react-native';
import { useRideHistory } from '../../src/hooks/useUserQueries';
import { format } from 'date-fns';
import { AlertTriangle, Clock } from 'lucide-react-native';

export default function HistoryScreen() {
  const { data: history, isLoading, error } = useRideHistory();

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#3b82f6" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={{ color: 'red' }}>Failed to load history.</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={history}
        keyExtractor={item => item.rideId}
        contentContainerStyle={{ padding: 20 }}
        ListEmptyComponent={<Text style={styles.emptyText}>No rides found.</Text>}
        renderItem={({ item }) => (
          <View style={[styles.card, item.alertCount > 0 && styles.cardDanger]}>
            <View style={styles.cardHeader}>
              <Text style={styles.dateText}>
                {format(new Date(item.startTime), 'MMM dd, yyyy - HH:mm')}
              </Text>
              {item.alertCount > 0 && (
                <View style={styles.alertBadge}>
                  <AlertTriangle size={12} color="#ef4444" />
                  <Text style={styles.alertText}>{item.alertCount} Alerts</Text>
                </View>
              )}
            </View>
            
            <View style={styles.row}>
              <View style={styles.statBox}>
                <Clock size={16} color="#64748b" />
                <Text style={styles.statText}>{item.durationMinutes.toFixed(1)} min</Text>
              </View>
            </View>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyText: {
    textAlign: 'center',
    color: '#64748b',
    marginTop: 40,
  },
  card: {
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 5,
    elevation: 2,
    borderLeftWidth: 4,
    borderLeftColor: '#3b82f6',
  },
  cardDanger: {
    borderLeftColor: '#ef4444',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  dateText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#0f172a',
  },
  alertBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#fee2e2',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  alertText: {
    fontSize: 12,
    color: '#ef4444',
    fontWeight: 'bold',
  },
  row: {
    flexDirection: 'row',
    gap: 16,
  },
  statBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  statText: {
    fontSize: 14,
    color: '#64748b',
  }
});
