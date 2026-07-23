// SPDX-License-Identifier: LGPL-2.1-or-later

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <limits>
#include <queue>
#include <stdexcept>
#include <string>
#include <vector>

#include <BOPAlgo_ArgumentAnalyzer.hxx>
#include <BOPAlgo_ListOfCheckResult.hxx>
#include <BRepBndLib.hxx>
#include <BRepBuilderAPI_Copy.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepCheck_ListOfStatus.hxx>
#include <BRepCheck_Result.hxx>
#include <BRepExtrema_DistShapeShape.hxx>
#include <BRepGProp.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <Bnd_Box.hxx>
#include <GProp_GProps.hxx>
#include <Message_ProgressIndicator.hxx>
#include <Precision.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS_Shape.hxx>
#include <gp_Pnt.hxx>
#include <nlohmann/json.hpp>

namespace
{

using Clock = std::chrono::steady_clock;
using Json = nlohmann::json;

struct Vec3
{
    double x {0.0};
    double y {0.0};
    double z {0.0};
};

Vec3 operator+(const Vec3& lhs, const Vec3& rhs)
{
    return {lhs.x + rhs.x, lhs.y + rhs.y, lhs.z + rhs.z};
}

Vec3 operator-(const Vec3& lhs, const Vec3& rhs)
{
    return {lhs.x - rhs.x, lhs.y - rhs.y, lhs.z - rhs.z};
}

Vec3 operator*(const Vec3& value, double scalar)
{
    return {value.x * scalar, value.y * scalar, value.z * scalar};
}

double dot(const Vec3& lhs, const Vec3& rhs)
{
    return lhs.x * rhs.x + lhs.y * rhs.y + lhs.z * rhs.z;
}

Vec3 cross(const Vec3& lhs, const Vec3& rhs)
{
    return {
        lhs.y * rhs.z - lhs.z * rhs.y,
        lhs.z * rhs.x - lhs.x * rhs.z,
        lhs.x * rhs.y - lhs.y * rhs.x,
    };
}

double normSquared(const Vec3& value)
{
    return dot(value, value);
}

Json pointJson(const Vec3& point)
{
    return Json::array({point.x, point.y, point.z});
}

Json pointJson(const gp_Pnt& point)
{
    return Json::array({point.X(), point.Y(), point.Z()});
}

struct Triangle
{
    std::array<Vec3, 3> points;
};

struct Bounds
{
    Vec3 minimum {
        std::numeric_limits<double>::infinity(),
        std::numeric_limits<double>::infinity(),
        std::numeric_limits<double>::infinity(),
    };
    Vec3 maximum {
        -std::numeric_limits<double>::infinity(),
        -std::numeric_limits<double>::infinity(),
        -std::numeric_limits<double>::infinity(),
    };

    void add(const Vec3& point)
    {
        minimum.x = std::min(minimum.x, point.x);
        minimum.y = std::min(minimum.y, point.y);
        minimum.z = std::min(minimum.z, point.z);
        maximum.x = std::max(maximum.x, point.x);
        maximum.y = std::max(maximum.y, point.y);
        maximum.z = std::max(maximum.z, point.z);
    }

    void add(const Bounds& other)
    {
        add(other.minimum);
        add(other.maximum);
    }
};

Bounds triangleBounds(const Triangle& triangle)
{
    Bounds result;
    for (const Vec3& point : triangle.points) {
        result.add(point);
    }
    return result;
}

Vec3 triangleCenter(const Triangle& triangle)
{
    return (triangle.points[0] + triangle.points[1] + triangle.points[2]) * (1.0 / 3.0);
}

double boundsDistanceSquared(const Bounds& first, const Bounds& second)
{
    double result = 0.0;
    for (int axis = 0; axis < 3; ++axis) {
        const double firstMin = axis == 0 ? first.minimum.x : axis == 1 ? first.minimum.y
                                                                        : first.minimum.z;
        const double firstMax = axis == 0 ? first.maximum.x : axis == 1 ? first.maximum.y
                                                                        : first.maximum.z;
        const double secondMin = axis == 0 ? second.minimum.x : axis == 1 ? second.minimum.y
                                                                           : second.minimum.z;
        const double secondMax = axis == 0 ? second.maximum.x : axis == 1 ? second.maximum.y
                                                                           : second.maximum.z;
        double separation = 0.0;
        if (firstMax < secondMin) {
            separation = secondMin - firstMax;
        }
        else if (secondMax < firstMin) {
            separation = firstMin - secondMax;
        }
        result += separation * separation;
    }
    return result;
}

struct ClosestPair
{
    double distanceSquared {std::numeric_limits<double>::infinity()};
    Vec3 first;
    Vec3 second;
};

void consider(ClosestPair& best, const Vec3& first, const Vec3& second)
{
    const double candidate = normSquared(first - second);
    if (candidate < best.distanceSquared) {
        best = {candidate, first, second};
    }
}

Vec3 closestPointOnTriangle(const Vec3& point, const Triangle& triangle)
{
    const Vec3& a = triangle.points[0];
    const Vec3& b = triangle.points[1];
    const Vec3& c = triangle.points[2];
    const Vec3 ab = b - a;
    const Vec3 ac = c - a;
    const Vec3 ap = point - a;
    const double d1 = dot(ab, ap);
    const double d2 = dot(ac, ap);
    if (d1 <= 0.0 && d2 <= 0.0) {
        return a;
    }

    const Vec3 bp = point - b;
    const double d3 = dot(ab, bp);
    const double d4 = dot(ac, bp);
    if (d3 >= 0.0 && d4 <= d3) {
        return b;
    }

    const double vc = d1 * d4 - d3 * d2;
    if (vc <= 0.0 && d1 >= 0.0 && d3 <= 0.0) {
        const double v = d1 / (d1 - d3);
        return a + ab * v;
    }

    const Vec3 cp = point - c;
    const double d5 = dot(ab, cp);
    const double d6 = dot(ac, cp);
    if (d6 >= 0.0 && d5 <= d6) {
        return c;
    }

    const double vb = d5 * d2 - d1 * d6;
    if (vb <= 0.0 && d2 >= 0.0 && d6 <= 0.0) {
        const double w = d2 / (d2 - d6);
        return a + ac * w;
    }

    const double va = d3 * d6 - d5 * d4;
    if (va <= 0.0 && (d4 - d3) >= 0.0 && (d5 - d6) >= 0.0) {
        const Vec3 bc = c - b;
        const double w = (d4 - d3) / ((d4 - d3) + (d5 - d6));
        return b + bc * w;
    }

    const double denominator = 1.0 / (va + vb + vc);
    const double v = vb * denominator;
    const double w = vc * denominator;
    return a + ab * v + ac * w;
}

ClosestPair closestSegmentPair(
    const Vec3& firstStart,
    const Vec3& firstEnd,
    const Vec3& secondStart,
    const Vec3& secondEnd
)
{
    constexpr double epsilon = 1e-18;
    const Vec3 firstDirection = firstEnd - firstStart;
    const Vec3 secondDirection = secondEnd - secondStart;
    const Vec3 offset = firstStart - secondStart;
    const double firstLength = dot(firstDirection, firstDirection);
    const double secondLength = dot(secondDirection, secondDirection);
    const double mixed = dot(secondDirection, offset);
    double firstParameter = 0.0;
    double secondParameter = 0.0;

    if (firstLength <= epsilon && secondLength <= epsilon) {
        return {normSquared(firstStart - secondStart), firstStart, secondStart};
    }
    if (firstLength <= epsilon) {
        secondParameter = std::clamp(mixed / secondLength, 0.0, 1.0);
    }
    else {
        const double firstOffset = dot(firstDirection, offset);
        if (secondLength <= epsilon) {
            firstParameter = std::clamp(-firstOffset / firstLength, 0.0, 1.0);
        }
        else {
            const double coupling = dot(firstDirection, secondDirection);
            const double denominator = firstLength * secondLength - coupling * coupling;
            if (denominator > epsilon) {
                firstParameter = std::clamp(
                    (coupling * mixed - firstOffset * secondLength) / denominator,
                    0.0,
                    1.0
                );
            }
            secondParameter = (coupling * firstParameter + mixed) / secondLength;
            if (secondParameter < 0.0) {
                secondParameter = 0.0;
                firstParameter = std::clamp(-firstOffset / firstLength, 0.0, 1.0);
            }
            else if (secondParameter > 1.0) {
                secondParameter = 1.0;
                firstParameter = std::clamp(
                    (coupling - firstOffset) / firstLength,
                    0.0,
                    1.0
                );
            }
        }
    }
    const Vec3 firstPoint = firstStart + firstDirection * firstParameter;
    const Vec3 secondPoint = secondStart + secondDirection * secondParameter;
    return {normSquared(firstPoint - secondPoint), firstPoint, secondPoint};
}

bool segmentTriangleIntersection(
    const Vec3& start,
    const Vec3& end,
    const Triangle& triangle,
    Vec3& intersection
)
{
    constexpr double epsilon = 1e-12;
    const Vec3 direction = end - start;
    const Vec3 edge1 = triangle.points[1] - triangle.points[0];
    const Vec3 edge2 = triangle.points[2] - triangle.points[0];
    const Vec3 p = cross(direction, edge2);
    const double determinant = dot(edge1, p);
    if (std::abs(determinant) <= epsilon) {
        return false;
    }
    const double inverse = 1.0 / determinant;
    const Vec3 translated = start - triangle.points[0];
    const double u = dot(translated, p) * inverse;
    if (u < -epsilon || u > 1.0 + epsilon) {
        return false;
    }
    const Vec3 q = cross(translated, edge1);
    const double v = dot(direction, q) * inverse;
    if (v < -epsilon || u + v > 1.0 + epsilon) {
        return false;
    }
    const double parameter = dot(edge2, q) * inverse;
    if (parameter < -epsilon || parameter > 1.0 + epsilon) {
        return false;
    }
    intersection = start + direction * std::clamp(parameter, 0.0, 1.0);
    return true;
}

ClosestPair closestTrianglePair(const Triangle& first, const Triangle& second)
{
    ClosestPair best;
    for (int edge = 0; edge < 3; ++edge) {
        Vec3 intersection;
        if (segmentTriangleIntersection(
                first.points[edge],
                first.points[(edge + 1) % 3],
                second,
                intersection
            )) {
            return {0.0, intersection, intersection};
        }
        if (segmentTriangleIntersection(
                second.points[edge],
                second.points[(edge + 1) % 3],
                first,
                intersection
            )) {
            return {0.0, intersection, intersection};
        }
    }
    for (const Vec3& point : first.points) {
        consider(best, point, closestPointOnTriangle(point, second));
    }
    for (const Vec3& point : second.points) {
        consider(best, closestPointOnTriangle(point, first), point);
    }
    for (int firstEdge = 0; firstEdge < 3; ++firstEdge) {
        for (int secondEdge = 0; secondEdge < 3; ++secondEdge) {
            const ClosestPair candidate = closestSegmentPair(
                first.points[firstEdge],
                first.points[(firstEdge + 1) % 3],
                second.points[secondEdge],
                second.points[(secondEdge + 1) % 3]
            );
            consider(best, candidate.first, candidate.second);
        }
    }
    return best;
}

std::vector<Triangle> readStl(const std::filesystem::path& path)
{
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw std::runtime_error("Cannot open STL artifact: " + path.string());
    }
    input.seekg(0, std::ios::end);
    const std::streamoff size = input.tellg();
    input.seekg(80, std::ios::beg);
    std::uint32_t triangleCount = 0;
    input.read(reinterpret_cast<char*>(&triangleCount), sizeof(triangleCount));
    const std::uint64_t expected = 84ULL + 50ULL * triangleCount;
    if (input && size == static_cast<std::streamoff>(expected)) {
        std::vector<Triangle> triangles;
        triangles.reserve(triangleCount);
        input.seekg(84, std::ios::beg);
        for (std::uint32_t index = 0; index < triangleCount; ++index) {
            std::array<float, 12> record {};
            input.read(reinterpret_cast<char*>(record.data()), 48);
            std::uint16_t attribute = 0;
            input.read(reinterpret_cast<char*>(&attribute), sizeof(attribute));
            if (!input) {
                throw std::runtime_error("Binary STL ended before its declared triangle count.");
            }
            Triangle triangle;
            for (int vertex = 0; vertex < 3; ++vertex) {
                triangle.points[vertex] = {
                    record[3 + vertex * 3],
                    record[4 + vertex * 3],
                    record[5 + vertex * 3],
                };
            }
            triangles.push_back(triangle);
        }
        return triangles;
    }

    input.close();
    std::ifstream text(path);
    if (!text) {
        throw std::runtime_error("Cannot reopen ASCII STL artifact: " + path.string());
    }
    std::vector<Triangle> triangles;
    std::string token;
    std::vector<Vec3> vertices;
    while (text >> token) {
        if (token != "vertex") {
            continue;
        }
        Vec3 point;
        if (!(text >> point.x >> point.y >> point.z)) {
            throw std::runtime_error("ASCII STL contains an invalid vertex record.");
        }
        vertices.push_back(point);
        if (vertices.size() == 3) {
            triangles.push_back({{vertices[0], vertices[1], vertices[2]}});
            vertices.clear();
        }
    }
    if (triangles.empty() || !vertices.empty()) {
        throw std::runtime_error("STL artifact contains no complete triangles.");
    }
    return triangles;
}

struct BvhNode
{
    Bounds bounds;
    std::size_t begin {0};
    std::size_t count {0};
    int left {-1};
    int right {-1};

    bool leaf() const
    {
        return left < 0;
    }
};

class TriangleBvh
{
public:
    explicit TriangleBvh(std::vector<Triangle> input)
        : triangles(std::move(input))
    {
        if (triangles.empty()) {
            throw std::runtime_error("Cannot build a BVH for an empty mesh.");
        }
        order.resize(triangles.size());
        for (std::size_t index = 0; index < order.size(); ++index) {
            order[index] = index;
        }
        build(0, order.size());
    }

    std::vector<Triangle> triangles;
    std::vector<std::size_t> order;
    std::vector<BvhNode> nodes;

private:
    int build(std::size_t begin, std::size_t end)
    {
        const int nodeIndex = static_cast<int>(nodes.size());
        nodes.emplace_back();
        Bounds bounds;
        Bounds centers;
        for (std::size_t index = begin; index < end; ++index) {
            const Triangle& triangle = triangles[order[index]];
            bounds.add(triangleBounds(triangle));
            centers.add(triangleCenter(triangle));
        }
        nodes[nodeIndex].bounds = bounds;
        nodes[nodeIndex].begin = begin;
        nodes[nodeIndex].count = end - begin;
        if (end - begin <= 8) {
            return nodeIndex;
        }
        const Vec3 extent = centers.maximum - centers.minimum;
        const int axis = extent.x >= extent.y && extent.x >= extent.z ? 0
            : extent.y >= extent.z                                ? 1
                                                                 : 2;
        const std::size_t middle = begin + (end - begin) / 2;
        std::nth_element(
            order.begin() + static_cast<std::ptrdiff_t>(begin),
            order.begin() + static_cast<std::ptrdiff_t>(middle),
            order.begin() + static_cast<std::ptrdiff_t>(end),
            [&](std::size_t lhs, std::size_t rhs) {
                const Vec3 leftCenter = triangleCenter(triangles[lhs]);
                const Vec3 rightCenter = triangleCenter(triangles[rhs]);
                return axis == 0 ? leftCenter.x < rightCenter.x
                    : axis == 1  ? leftCenter.y < rightCenter.y
                                 : leftCenter.z < rightCenter.z;
            }
        );
        const int left = build(begin, middle);
        const int right = build(middle, end);
        nodes[nodeIndex].left = left;
        nodes[nodeIndex].right = right;
        nodes[nodeIndex].count = 0;
        return nodeIndex;
    }
};

ClosestPair meshDistance(const TriangleBvh& first, const TriangleBvh& second)
{
    struct Candidate
    {
        double lowerBound;
        int firstNode;
        int secondNode;
    };
    struct FartherFirst
    {
        bool operator()(const Candidate& lhs, const Candidate& rhs) const
        {
            return lhs.lowerBound > rhs.lowerBound;
        }
    };
    std::priority_queue<Candidate, std::vector<Candidate>, FartherFirst> pending;
    pending.push({boundsDistanceSquared(first.nodes[0].bounds, second.nodes[0].bounds), 0, 0});
    ClosestPair best;
    while (!pending.empty()) {
        const Candidate candidate = pending.top();
        pending.pop();
        if (candidate.lowerBound >= best.distanceSquared) {
            continue;
        }
        const BvhNode& firstNode = first.nodes[candidate.firstNode];
        const BvhNode& secondNode = second.nodes[candidate.secondNode];
        if (firstNode.leaf() && secondNode.leaf()) {
            for (std::size_t firstOffset = 0; firstOffset < firstNode.count; ++firstOffset) {
                const Triangle& firstTriangle =
                    first.triangles[first.order[firstNode.begin + firstOffset]];
                for (std::size_t secondOffset = 0; secondOffset < secondNode.count;
                     ++secondOffset) {
                    const Triangle& secondTriangle =
                        second.triangles[second.order[secondNode.begin + secondOffset]];
                    const ClosestPair measured =
                        closestTrianglePair(firstTriangle, secondTriangle);
                    if (measured.distanceSquared < best.distanceSquared) {
                        best = measured;
                    }
                    if (best.distanceSquared <= 1e-24) {
                        return best;
                    }
                }
            }
            continue;
        }
        const auto enqueue = [&](int firstIndex, int secondIndex) {
            const double lower = boundsDistanceSquared(
                first.nodes[firstIndex].bounds,
                second.nodes[secondIndex].bounds
            );
            if (lower < best.distanceSquared) {
                pending.push({lower, firstIndex, secondIndex});
            }
        };
        if (firstNode.leaf()) {
            enqueue(candidate.firstNode, secondNode.left);
            enqueue(candidate.firstNode, secondNode.right);
        }
        else if (secondNode.leaf()) {
            enqueue(firstNode.left, candidate.secondNode);
            enqueue(firstNode.right, candidate.secondNode);
        }
        else {
            enqueue(firstNode.left, secondNode.left);
            enqueue(firstNode.left, secondNode.right);
            enqueue(firstNode.right, secondNode.left);
            enqueue(firstNode.right, secondNode.right);
        }
    }
    return best;
}

class DeadlineProgressIndicator final : public Message_ProgressIndicator
{
public:
    explicit DeadlineProgressIndicator(std::chrono::milliseconds timeout)
        : deadline(Clock::now() + timeout)
    {}

    void Show(const Message_ProgressScope&, const Standard_Boolean) override
    {}

    Standard_Boolean UserBreak() override
    {
        return Clock::now() >= deadline;
    }

private:
    Clock::time_point deadline;
};

TopoDS_Shape readBrep(const std::filesystem::path& path)
{
    TopoDS_Shape shape;
    BRep_Builder builder;
    if (!BRepTools::Read(shape, path.string().c_str(), builder) || shape.IsNull()) {
        throw std::runtime_error("Cannot read BREP artifact: " + path.string());
    }
    return shape;
}

int subshapeCount(const TopoDS_Shape& shape, TopAbs_ShapeEnum type)
{
    TopTools_IndexedMapOfShape map;
    TopExp::MapShapes(shape, type, map);
    return map.Extent();
}

Json shapeFacts(const TopoDS_Shape& shape)
{
    Bnd_Box box;
    BRepBndLib::AddOptimal(shape, box, false, false);
    Standard_Real xMin = 0.0;
    Standard_Real yMin = 0.0;
    Standard_Real zMin = 0.0;
    Standard_Real xMax = 0.0;
    Standard_Real yMax = 0.0;
    Standard_Real zMax = 0.0;
    box.Get(xMin, yMin, zMin, xMax, yMax, zMax);
    GProp_GProps volume;
    GProp_GProps area;
    BRepGProp::VolumeProperties(shape, volume);
    BRepGProp::SurfaceProperties(shape, area);
    return {
        {"valid", BRepCheck_Analyzer(shape, true).IsValid()},
        {"solids", subshapeCount(shape, TopAbs_SOLID)},
        {"faces", subshapeCount(shape, TopAbs_FACE)},
        {"edges", subshapeCount(shape, TopAbs_EDGE)},
        {"vertices", subshapeCount(shape, TopAbs_VERTEX)},
        {"volume_mm3", volume.Mass()},
        {"area_mm2", area.Mass()},
        {"bbox",
         {{"min", Json::array({xMin, yMin, zMin})},
          {"max", Json::array({xMax, yMax, zMax})}}},
    };
}

std::string shapeTypeName(TopAbs_ShapeEnum type)
{
    static const std::array<const char*, 9> names {
        "compound",
        "compsolid",
        "solid",
        "shell",
        "face",
        "wire",
        "edge",
        "vertex",
        "shape",
    };
    const std::size_t index = static_cast<std::size_t>(type);
    return index < names.size() ? names[index] : "unknown";
}

std::string brepStatusName(BRepCheck_Status status)
{
    static const std::array<const char*, 34> names {
        "NoError",
        "InvalidPointOnCurve",
        "InvalidPointOnCurveOnSurface",
        "InvalidPointOnSurface",
        "No3DCurve",
        "Multiple3DCurve",
        "Invalid3DCurve",
        "NoCurveOnSurface",
        "InvalidCurveOnSurface",
        "InvalidCurveOnClosedSurface",
        "InvalidSameRangeFlag",
        "InvalidSameParameterFlag",
        "InvalidDegeneratedFlag",
        "FreeEdge",
        "InvalidMultiConnexity",
        "InvalidRange",
        "EmptyWire",
        "RedundantEdge",
        "SelfIntersectingWire",
        "NoSurface",
        "InvalidWire",
        "RedundantWire",
        "IntersectingWires",
        "InvalidImbricationOfWires",
        "EmptyShell",
        "RedundantFace",
        "UnorientableShape",
        "NotClosed",
        "NotConnected",
        "SubshapeNotInShape",
        "BadOrientation",
        "BadOrientationOfSubshape",
        "InvalidToleranceValue",
        "CheckFail",
    };
    const std::size_t index = static_cast<std::size_t>(status);
    return index < names.size() ? names[index] : "Unknown";
}

std::string bopStatusName(BOPAlgo_CheckStatus status)
{
    static const std::array<const char*, 12> names {
        "CheckUnknown",
        "BadType",
        "SelfIntersect",
        "TooSmallEdge",
        "NonRecoverableFace",
        "IncompatibilityOfVertex",
        "IncompatibilityOfEdge",
        "IncompatibilityOfFace",
        "OperationAborted",
        "GeomAbs_C0",
        "InvalidCurveOnSurface",
        "NotValid",
    };
    const std::size_t index = static_cast<std::size_t>(status);
    return index < names.size() ? names[index] : "Unknown";
}

Json brepDefects(const TopoDS_Shape& shape, BRepCheck_Analyzer& analyzer)
{
    static const std::array<TopAbs_ShapeEnum, 8> checkedTypes {
        TopAbs_VERTEX,
        TopAbs_EDGE,
        TopAbs_WIRE,
        TopAbs_FACE,
        TopAbs_SHELL,
        TopAbs_SOLID,
        TopAbs_COMPOUND,
        TopAbs_COMPSOLID,
    };
    Json defects = Json::array();
    for (const TopAbs_ShapeEnum type : checkedTypes) {
        TopTools_IndexedMapOfShape subshapes;
        TopExp::MapShapes(shape, type, subshapes);
        for (int index = 1; index <= subshapes.Extent(); ++index) {
            const TopoDS_Shape& subshape = subshapes(index);
            if (analyzer.IsValid(subshape)) {
                continue;
            }
            const Handle(BRepCheck_Result) & result = analyzer.Result(subshape);
            if (result.IsNull()) {
                defects.push_back(
                    {{"shape_type", shapeTypeName(type)},
                     {"shape_index", index},
                     {"status", "Unknown"},
                     {"status_code", -1}}
                );
                continue;
            }
            const BRepCheck_ListOfStatus& statuses = result->StatusOnShape(subshape);
            for (BRepCheck_ListIteratorOfListOfStatus iterator(statuses); iterator.More();
                 iterator.Next()) {
                const BRepCheck_Status status = iterator.Value();
                if (status == BRepCheck_NoError) {
                    continue;
                }
                defects.push_back(
                    {{"shape_type", shapeTypeName(type)},
                     {"shape_index", index},
                     {"status", brepStatusName(status)},
                     {"status_code", static_cast<int>(status)}}
                );
            }
        }
    }
    return defects;
}

void appendBopFaults(
    Json& defects,
    const BOPAlgo_CheckResult& result,
    const TopTools_ListOfShape& shapes,
    int argument
)
{
    int index = 0;
    for (TopTools_ListIteratorOfListOfShape iterator(shapes); iterator.More(); iterator.Next()) {
        ++index;
        const TopoDS_Shape& shape = iterator.Value();
        defects.push_back(
            {{"argument", argument},
             {"shape_type", shapeTypeName(shape.ShapeType())},
             {"shape_index", index},
             {"status", bopStatusName(result.GetCheckStatus())},
             {"status_code", static_cast<int>(result.GetCheckStatus())}}
        );
    }
}

Json bopDefects(const TopoDS_Shape& shape)
{
    const TopoDS_Shape copiedShape = BRepBuilderAPI_Copy(shape).Shape();
    BOPAlgo_ArgumentAnalyzer analyzer;
    analyzer.SetShape1(copiedShape);
    analyzer.ArgumentTypeMode() = true;
    analyzer.SelfInterMode() = true;
    analyzer.SmallEdgeMode() = true;
    analyzer.RebuildFaceMode() = true;
    analyzer.ContinuityMode() = true;
    analyzer.SetParallelMode(true);
    analyzer.SetRunParallel(true);
    analyzer.TangentMode() = true;
    analyzer.MergeVertexMode() = true;
    analyzer.CurveOnSurfaceMode() = true;
    analyzer.MergeEdgeMode() = true;
    analyzer.Perform();

    Json defects = Json::array();
    for (BOPAlgo_ListIteratorOfListOfCheckResult iterator(analyzer.GetCheckResult());
         iterator.More();
         iterator.Next()) {
        const BOPAlgo_CheckResult& result = iterator.Value();
        const std::size_t previousSize = defects.size();
        appendBopFaults(defects, result, result.GetFaultyShapes1(), 1);
        appendBopFaults(defects, result, result.GetFaultyShapes2(), 2);
        if (defects.size() == previousSize) {
            defects.push_back(
                {{"argument", 0},
                 {"shape_type", "unknown"},
                 {"shape_index", 0},
                 {"status", bopStatusName(result.GetCheckStatus())},
                 {"status_code", static_cast<int>(result.GetCheckStatus())}}
            );
        }
    }
    return defects;
}

Json validateBrep(const Json& request)
{
    const TopoDS_Shape shape = readBrep(request.at("shape").at("path").get<std::string>());
    BRepCheck_Analyzer brepAnalyzer(shape);
    const bool brepValid = brepAnalyzer.IsValid();
    Json brep = {
        {"valid", brepValid},
        {"defects", brepValid ? Json::array() : brepDefects(shape, brepAnalyzer)},
    };

    Json bop;
    bool valid = false;
    if (brepValid) {
        Json defects = bopDefects(shape);
        valid = defects.empty();
        bop = {
            {"performed", true},
            {"valid", valid},
            {"defects", std::move(defects)},
        };
    }
    else {
        bop = {
            {"performed", false},
            {"valid", nullptr},
            {"defects", Json::array()},
            {"reason", "BOP analysis skipped because BRepCheck rejected the shape."},
        };
    }
    return {
        {"ok", true},
        {"operation", "validate_brep"},
        {"valid", valid},
        {"brep", std::move(brep)},
        {"bop", std::move(bop)},
    };
}

Json brepMinimumDistance(const Json& request)
{
    const TopoDS_Shape first = readBrep(request.at("first").at("path").get<std::string>());
    const TopoDS_Shape second = readBrep(request.at("second").at("path").get<std::string>());
    const double tolerance = request.value("tolerance", Precision::Confusion());
    const auto timeout = std::chrono::milliseconds(request.value("deadline_ms", 30000));
    Handle(DeadlineProgressIndicator) progress = new DeadlineProgressIndicator(timeout);
    BRepExtrema_DistShapeShape extrema;
    extrema.SetDeflection(tolerance);
    extrema.SetMultiThread(true);
    extrema.LoadS1(first);
    extrema.LoadS2(second);
    extrema.Perform(Message_ProgressIndicator::Start(progress));
    if (progress->UserBreak()) {
        throw std::runtime_error("Geometry distance exceeded its native deadline.");
    }
    if (!extrema.IsDone() || extrema.NbSolution() < 1) {
        throw std::runtime_error("BRepExtrema_DistShapeShape returned no solution.");
    }
    Json pairs = Json::array();
    for (int index = 1; index <= extrema.NbSolution(); ++index) {
        pairs.push_back(
            {{"first", pointJson(extrema.PointOnShape1(index))},
             {"second", pointJson(extrema.PointOnShape2(index))}}
        );
    }
    return {
        {"ok", true},
        {"fidelity", request.value("fidelity", "exact_brep")},
        {"calculation", "isolated_opencascade_bounded_shape_to_shape"},
        {"distance", extrema.Value()},
        {"closest_point_pairs", pairs},
        {"first_shape", shapeFacts(first)},
        {"second_shape", shapeFacts(second)},
    };
}

Json stlMinimumDistance(const Json& request)
{
    const TriangleBvh first(readStl(request.at("first").at("path").get<std::string>()));
    const TriangleBvh second(readStl(request.at("second").at("path").get<std::string>()));
    const ClosestPair measured = meshDistance(first, second);
    if (!std::isfinite(measured.distanceSquared)) {
        throw std::runtime_error("The faceted distance solver returned no solution.");
    }
    return {
        {"ok", true},
        {"fidelity", "faceted_brep"},
        {"calculation", "isolated_exact_triangle_bvh"},
        {"distance", std::sqrt(std::max(0.0, measured.distanceSquared))},
        {"closest_point_pairs",
         Json::array({{{"first", pointJson(measured.first)},
                       {"second", pointJson(measured.second)}}})},
        {"first_shape", {{"triangles", first.triangles.size()}}},
        {"second_shape", {{"triangles", second.triangles.size()}}},
    };
}

void writeJson(const std::filesystem::path& path, const Json& payload)
{
    const std::filesystem::path temporary = path.string() + ".tmp";
    std::ofstream output(temporary, std::ios::trunc);
    if (!output) {
        throw std::runtime_error("Cannot open geometry result path: " + path.string());
    }
    output << payload.dump(2) << '\n';
    output.close();
    std::filesystem::rename(temporary, path);
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 2) {
        return 2;
    }
    std::filesystem::path resultPath;
    const auto started = Clock::now();
    try {
        std::ifstream input(argv[1]);
        if (!input) {
            throw std::runtime_error("Cannot open geometry request file.");
        }
        Json request;
        input >> request;
        if (request.value("schema", "") != "cadex-geometry-job-v1") {
            throw std::runtime_error("Unsupported geometry request schema.");
        }
        resultPath = request.at("result_path").get<std::string>();
        const std::string operation = request.value("operation", "");
        Json result;
        if (operation == "validate_brep") {
            if (request.at("shape").at("format").get<std::string>() != "brep") {
                throw std::runtime_error("Shape validation requires a BREP artifact.");
            }
            result = validateBrep(request);
        }
        else if (operation == "minimum_distance") {
            const std::string firstFormat = request.at("first").at("format").get<std::string>();
            const std::string secondFormat =
                request.at("second").at("format").get<std::string>();
            if (firstFormat == "brep" && secondFormat == "brep") {
                result = brepMinimumDistance(request);
            }
            else if (firstFormat == "stl" && secondFormat == "stl") {
                result = stlMinimumDistance(request);
            }
            else {
                throw std::runtime_error(
                    "Geometry artifacts must both be BREP or both be STL for one distance job."
                );
            }
        }
        else {
            throw std::runtime_error("Unsupported geometry worker operation.");
        }
        result["schema"] = "cadex-geometry-result-v1";
        result["elapsed_ms"] = std::chrono::duration_cast<std::chrono::milliseconds>(
                                   Clock::now() - started
        )
                                   .count();
        writeJson(resultPath, result);
        return 0;
    }
    catch (const Standard_Failure& error) {
        if (!resultPath.empty()) {
            writeJson(
                resultPath,
                {{"schema", "cadex-geometry-result-v1"},
                 {"ok", false},
                 {"failure_stage", "native_call"},
                 {"exception_type", "Standard_Failure"},
                 {"error", error.GetMessageString() ? error.GetMessageString() : "OpenCascade failure"}}
            );
        }
        return 1;
    }
    catch (const std::exception& error) {
        if (!resultPath.empty()) {
            writeJson(
                resultPath,
                {{"schema", "cadex-geometry-result-v1"},
                 {"ok", false},
                 {"failure_stage", "native_call"},
                 {"exception_type", "std::exception"},
                 {"error", error.what()}}
            );
        }
        return 1;
    }
}
