/**
 * SearchHeader component - displays page title
 */

import { UI_TEXT } from '../constants';

export const SearchHeader: React.FC = () => {
  return <h1 className="text-2xl font-bold mb-6">{UI_TEXT.PAGE_TITLE}</h1>;
};
