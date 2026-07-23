// SPDX-License-Identifier: LGPL-2.1-or-later

#include "FeaturePy.h"

#include <Mod/Part/App/TopoShapePy.h>

#include "FeatureRefine.h"

using namespace PartDesign;

PyObject* FeaturePy::getUnrefinedShape(PyObject* /*args*/)
{
    auto* feature = dynamic_cast<FeatureRefine*>(getFeaturePtr());
    if (!feature) {
        return new Part::TopoShapePy(new Part::TopoShape());
    }
    return new Part::TopoShapePy(new Part::TopoShape(feature->getUnrefinedShape()));
}
