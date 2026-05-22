import React, { useState, useEffect } from 'react';
import { Modal, View, Text, StyleSheet } from 'react-native';
import { SafeButton } from './SafeButton';

interface SOSModalProps {
  visible: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export const SOSModal: React.FC<SOSModalProps> = ({ visible, onCancel, onConfirm }) => {
  const [countdown, setCountdown] = useState(5);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    if (visible && countdown > 0) {
      timer = setTimeout(() => setCountdown(c => c - 1), 1000);
    } else if (visible && countdown === 0) {
      // Auto confirm when countdown reaches 0
      onConfirm();
      setCountdown(5); // Reset for next time
    }
    return () => clearTimeout(timer);
  }, [visible, countdown, onConfirm]);

  // Reset countdown if modal is closed manually
  useEffect(() => {
    if (!visible) {
      setCountdown(5);
    }
  }, [visible]);

  return (
    <Modal visible={visible} transparent animationType="fade">
      <View style={styles.overlay}>
        <View style={styles.container}>
          <View style={styles.warningCircle}>
            <Text style={styles.countdownText}>{countdown}</Text>
          </View>
          <Text style={styles.title}>Emergency SOS</Text>
          <Text style={styles.message}>
            Sending emergency signal to server and emergency contacts in {countdown} seconds...
          </Text>
          
          <View style={styles.buttonContainer}>
            <SafeButton 
              title="Cancel (False Alarm)" 
              onPress={onCancel} 
              variant="secondary" 
              style={styles.cancelBtn} 
            />
            <SafeButton 
              title="Send Now" 
              onPress={onConfirm} 
              variant="danger" 
              style={styles.confirmBtn} 
            />
          </View>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  container: {
    backgroundColor: '#ffffff',
    borderRadius: 20,
    padding: 24,
    alignItems: 'center',
    width: '100%',
    maxWidth: 400,
  },
  warningCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#fee2e2',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
    borderWidth: 2,
    borderColor: '#ef4444',
  },
  countdownText: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#ef4444',
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#0f172a',
  },
  message: {
    fontSize: 15,
    color: '#64748b',
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 22,
  },
  buttonContainer: {
    width: '100%',
    gap: 12,
  },
  cancelBtn: {
    width: '100%',
    backgroundColor: '#94a3b8',
  },
  confirmBtn: {
    width: '100%',
  }
});
