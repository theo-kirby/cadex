// SPDX-License-Identifier: LGPL-2.1-or-later

/***************************************************************************
 *   Copyright (c) 2017 Shai Seger <shaise at gmail>                       *
 *                                                                         *
 *   This file is part of the FreeCAD CAx development system.              *
 *                                                                         *
 *   This library is free software; you can redistribute it and/or         *
 *   modify it under the terms of the GNU Library General Public           *
 *   License as published by the Free Software Foundation; either          *
 *   version 2 of the License, or (at your option) any later version.      *
 *                                                                         *
 *   This library  is distributed in the hope that it will be useful,      *
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
 *   GNU Library General Public License for more details.                  *
 *                                                                         *
 *   You should have received a copy of the GNU Library General Public     *
 *   License along with this library; see the file COPYING.LIB. If not,    *
 *   write to the Free Software Foundation, Inc., 59 Temple Place,         *
 *   Suite 330, Boston, MA  02111-1307, USA                                *
 *                                                                         *
 ***************************************************************************/


#include "PathSim.h"


using namespace Base;
using namespace PathSimulator;

TYPESYSTEM_SOURCE(PathSimulator::PathSim, Base::BaseClass);

PathSim::PathSim()
{}

PathSim::~PathSim()
{}

void PathSim::BeginSimulation(Part::TopoShape* stock, float resolution)
{
    Base::BoundBox3d bbox = stock->getBoundBox();
    m_stock = std::make_unique<cStock>(
        bbox.MinX,
        bbox.MinY,
        bbox.MinZ,
        bbox.LengthX(),
        bbox.LengthY(),
        bbox.LengthZ(),
        resolution
    );
    m_cutCommands = 0;
    m_rapidCommands = 0;
    m_unsupportedCommands = 0;
}

void PathSim::SetToolShape(const TopoDS_Shape& toolShape, float resolution)
{
    m_tool = std::make_unique<cSimTool>(toolShape, resolution);
}

Base::Placement* PathSim::ApplyCommand(Base::Placement* pos, Command* cmd)
{
    Point3D fromPos(*pos);
    Point3D toPos(*pos);
    toPos.UpdateCmd(*cmd);
    if (m_tool) {
        if (cmd->Name == "G0" || cmd->Name == "G00") {
            ++m_rapidCommands;
        }
        else if (cmd->Name == "G1" || cmd->Name == "G01") {
            m_stock->ApplyLinearTool(fromPos, toPos, *m_tool);
            ++m_cutCommands;
        }
        else if (cmd->Name == "G2" || cmd->Name == "G02") {
            Vector3d vcent = cmd->getCenter();
            Point3D cent(vcent);
            m_stock->ApplyCircularTool(fromPos, toPos, cent, *m_tool, false);
            ++m_cutCommands;
        }
        else if (cmd->Name == "G3" || cmd->Name == "G03") {
            Vector3d vcent = cmd->getCenter();
            Point3D cent(vcent);
            m_stock->ApplyCircularTool(fromPos, toPos, cent, *m_tool, true);
            ++m_cutCommands;
        }
        else {
            ++m_unsupportedCommands;
        }
    }

    Base::Placement* plc = new Base::Placement();
    Vector3d vec(toPos.x, toPos.y, toPos.z);
    plc->setPosition(vec);
    return plc;
}

cStock::Statistics PathSim::GetSimulationStats() const
{
    if (!m_stock) {
        throw Base::RuntimeError("Simulation has no stock object");
    }
    return m_stock->GetStatistics();
}
