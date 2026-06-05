import React, { createContext, useCallback, useContext, useState } from 'react';

export type EmergencySource = 'user' | 'server';

export interface EmergencyState {
  visible: boolean;
  emergencyId?: string;
  reason: string;
  source: EmergencySource;
}

interface EmergencyContextValue {
  emergencyState: EmergencyState;
  triggerSOS: (params?: {
    reason?: string;
    emergencyId?: string;
    source?: EmergencySource;
  }) => void;
  dismissSOS: () => void;
}

const INITIAL_STATE: EmergencyState = {
  visible: false,
  reason: '',
  source: 'user',
};

const EmergencyContext = createContext<EmergencyContextValue | null>(null);

export const EmergencyProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [emergencyState, setEmergencyState] = useState<EmergencyState>(INITIAL_STATE);

  const triggerSOS = useCallback((params?: {
    reason?: string;
    emergencyId?: string;
    source?: EmergencySource;
  }) => {
    setEmergencyState({
      visible: true,
      reason: params?.reason ?? 'Emergency detected',
      emergencyId: params?.emergencyId,
      source: params?.source ?? 'user',
    });
  }, []);

  const dismissSOS = useCallback(() => {
    setEmergencyState(INITIAL_STATE);
  }, []);

  return (
    <EmergencyContext.Provider value={{ emergencyState, triggerSOS, dismissSOS }}>
      {children}
    </EmergencyContext.Provider>
  );
};

export const useEmergency = (): EmergencyContextValue => {
  const ctx = useContext(EmergencyContext);
  if (!ctx) throw new Error('useEmergency must be used within EmergencyProvider');
  return ctx;
};
