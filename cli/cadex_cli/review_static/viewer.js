// SPDX-License-Identifier: LGPL-2.1-or-later
import {create} from './review_scene.js';
import {parseStl} from './stl.js';
window.CadexViewer = {create,parseStl};
await import('./review.js');
