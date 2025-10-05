import React, { useState } from 'react';
import { Info, X } from 'lucide-react';
import { SUPPORTED_FORMATS, UI_TEXT } from '../constants';

export const SupportedFormats: React.FC = () => {
  const [showFormats, setShowFormats] = useState(false);

  return (
    <div className="mt-6">
      <button
        onClick={() => setShowFormats(!showFormats)}
        className="flex items-center space-x-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <Info className="h-4 w-4" />
        <span>{UI_TEXT.BUTTONS.VIEW_FORMATS}</span>
      </button>
      
      {showFormats && (
        <div className="mt-4 p-4 glass-card rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold">{UI_TEXT.FORMATS.TITLE}</h3>
            <button
              onClick={() => setShowFormats(false)}
              className="p-1 hover:bg-muted rounded transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            {SUPPORTED_FORMATS.map((format) => (
              <div key={format.category}>
                <h4 className={`font-medium ${format.categoryColor} mb-2`}>
                  {format.categoryIcon} {format.category}
                </h4>
                <ul className="space-y-1 text-muted-foreground">
                  {format.formats.map((item) => (
                    <li key={item.name} className={item.isNew ? 'font-medium' : ''}>
                      • {item.name} ({item.extensions})
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          
          <div className="mt-4 p-3 bg-green-50 dark:bg-green-950 rounded-md">
            <p className="text-xs text-green-700 dark:text-green-300">
              <strong>{UI_TEXT.FORMATS.NEW_FEATURE}</strong> {UI_TEXT.FORMATS.NEW_FEATURE_DESC}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};