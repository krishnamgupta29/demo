import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { DentraceStudioView } from './views/DentraceStudioView';

const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<DentraceStudioView />} />
      <Route path="/workstation" element={<DentraceStudioView />} />
    </Routes>
  );
};

export const App: React.FC = () => (
  <BrowserRouter>
    <AppRoutes />
  </BrowserRouter>
);

export default App;

