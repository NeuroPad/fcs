import React from 'react';
import './ContradictionBox.css';

interface ContradictionBoxProps {
  previousStatement: string;
  currentStatement: string;
  mode: 'contradiction' | 'track';
  visible: boolean;
  header: string;
  onChangeView: () => void;
  onTrackNewIdea: () => void;
}

const ContradictionBox: React.FC<ContradictionBoxProps> = ({
  previousStatement,
  currentStatement,
  mode,
  visible,
  header,
  onChangeView,
  onTrackNewIdea,
}) => {
  if (!visible) return null;

  return (
    <div className="contradiction-box">
      <div className="contradiction-header">
        {header}
      </div>
      <div className="contradiction-content">
        <div className="contradiction-previous">
          <strong>Previous:</strong> "{previousStatement}"
        </div>
        <div className="contradiction-current">
          <strong>Now:</strong> "{currentStatement}"
        </div>
      </div>
      <div className="contradiction-actions">
        <button className="contradiction-btn primary" onClick={onChangeView}>
          {mode === 'contradiction' ? 'Change my view to the new idea' : 'Adopt this new idea'}
        </button>
        <button className="contradiction-btn secondary" onClick={onTrackNewIdea}>
          {mode === 'contradiction' ? 'Track this as a new idea' : 'Just track, don\'t change view'}
        </button>
      </div>
    </div>
  );
};

export default ContradictionBox; 