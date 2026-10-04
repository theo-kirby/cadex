// SPDX-License-Identifier: LGPL-2.1-or-later
import {create} from './review_scene.js';
import {parseStl} from './stl.js';
import {layout as dimensionLayout} from './dimensions.js';
window.CadexViewer = {create,parseStl,dimensionLayout};
await import('./review.js');
