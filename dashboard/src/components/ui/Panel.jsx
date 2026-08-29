import React from 'react';

export default function Panel({ title, action, children, className = '', style = {} }) {
  return (
    <div className={`soc-panel ${className}`} style={style}>
      {title && (
        <div className="panel-header">
          <h3 className="panel-title">{title}</h3>
          {action && <div className="panel-action">{action}</div>}
        </div>
      )}
      <div className="panel-body">
        {children}
      </div>
    </div>
  );
}
