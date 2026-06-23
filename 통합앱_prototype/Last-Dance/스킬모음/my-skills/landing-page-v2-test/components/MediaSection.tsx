"use client"

export default function MediaSection() {
  return (
    <section className="py-20 bg-gradient-to-b from-background to-primary/5">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="mb-4">
              See It In Action
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Experience the beautiful, intuitive interface designed to make
              your workflow effortless and enjoyable.
            </p>
          </div>

          {/* Phone Mockups Grid */}
          <div className="grid md:grid-cols-3 gap-8 items-end">
            {/* Phone 1 */}
            <div className="group animate-fade-up" style={{ animationDelay: "100ms" }}>
              <div className="relative">
                {/* Phone Frame */}
                <div className="relative mx-auto w-64 h-[520px] bg-gray-900 rounded-[3rem] shadow-2xl border-8 border-gray-900 overflow-hidden transform transition-all duration-500 group-hover:scale-105 group-hover:rotate-1">
                  {/* Notch */}
                  <div className="absolute top-0 left-1/2 transform -translate-x-1/2 w-40 h-6 bg-gray-900 rounded-b-3xl z-10" />

                  {/* Screen Content */}
                  <div className="relative h-full bg-gradient-to-br from-purple-50 to-blue-50 p-6">
                    <div className="space-y-4">
                      {/* Header */}
                      <div className="flex items-center justify-between">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-accent" />
                        <div className="flex gap-2">
                          <div className="w-8 h-8 rounded-full bg-gray-200" />
                          <div className="w-8 h-8 rounded-full bg-gray-200" />
                        </div>
                      </div>

                      {/* Title */}
                      <div>
                        <div className="h-8 bg-gray-800 rounded w-3/4 mb-2" />
                        <div className="h-4 bg-gray-300 rounded w-1/2" />
                      </div>

                      {/* Cards */}
                      {[...Array(3)].map((_, i) => (
                        <div
                          key={i}
                          className="bg-white rounded-2xl p-4 shadow-md"
                          style={{ animationDelay: `${(i + 1) * 100}ms` }}
                        >
                          <div className="flex items-center gap-3 mb-2">
                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-accent opacity-80" />
                            <div className="flex-1">
                              <div className="h-3 bg-gray-200 rounded w-2/3 mb-1" />
                              <div className="h-2 bg-gray-100 rounded w-1/2" />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Label */}
                <div className="text-center mt-6">
                  <p className="font-semibold">Task Management</p>
                  <p className="text-sm text-muted-foreground">Stay organized effortlessly</p>
                </div>
              </div>
            </div>

            {/* Phone 2 - Center (Larger) */}
            <div className="group animate-fade-up md:-mb-8" style={{ animationDelay: "200ms" }}>
              <div className="relative">
                <div className="relative mx-auto w-72 h-[580px] bg-gray-900 rounded-[3rem] shadow-2xl border-8 border-gray-900 overflow-hidden transform transition-all duration-500 group-hover:scale-105">
                  <div className="absolute top-0 left-1/2 transform -translate-x-1/2 w-40 h-6 bg-gray-900 rounded-b-3xl z-10" />

                  <div className="relative h-full bg-gradient-to-br from-indigo-50 to-purple-50 p-6">
                    <div className="space-y-4">
                      <div className="flex items-center justify-between mb-6">
                        <div className="h-6 bg-gray-800 rounded w-1/3" />
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-accent" />
                      </div>

                      {/* Chart Representation */}
                      <div className="bg-white rounded-2xl p-6 shadow-lg">
                        <div className="h-4 bg-gray-800 rounded w-1/2 mb-4" />
                        <div className="flex items-end gap-2 h-32">
                          {[60, 80, 50, 90, 70, 95, 85].map((height, i) => (
                            <div
                              key={i}
                              className="flex-1 bg-gradient-to-t from-primary to-accent rounded-t opacity-80"
                              style={{ height: `${height}%` }}
                            />
                          ))}
                        </div>
                      </div>

                      {/* Stats Cards */}
                      <div className="grid grid-cols-2 gap-3">
                        {[...Array(4)].map((_, i) => (
                          <div key={i} className="bg-white rounded-xl p-3 shadow">
                            <div className="h-2 bg-gray-100 rounded w-3/4 mb-2" />
                            <div className="h-6 bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent font-bold" />
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="text-center mt-6">
                  <p className="font-semibold">Analytics Dashboard</p>
                  <p className="text-sm text-muted-foreground">Track your progress</p>
                </div>
              </div>
            </div>

            {/* Phone 3 */}
            <div className="group animate-fade-up" style={{ animationDelay: "300ms" }}>
              <div className="relative">
                <div className="relative mx-auto w-64 h-[520px] bg-gray-900 rounded-[3rem] shadow-2xl border-8 border-gray-900 overflow-hidden transform transition-all duration-500 group-hover:scale-105 group-hover:-rotate-1">
                  <div className="absolute top-0 left-1/2 transform -translate-x-1/2 w-40 h-6 bg-gray-900 rounded-b-3xl z-10" />

                  <div className="relative h-full bg-gradient-to-br from-cyan-50 to-blue-50 p-6">
                    <div className="space-y-4">
                      <div className="h-6 bg-gray-800 rounded w-1/2 mb-6" />

                      {/* Team Members */}
                      {[...Array(4)].map((_, i) => (
                        <div key={i} className="bg-white rounded-2xl p-4 shadow-md flex items-center gap-3">
                          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-accent to-primary" />
                          <div className="flex-1">
                            <div className="h-3 bg-gray-200 rounded w-3/4 mb-2" />
                            <div className="h-2 bg-gray-100 rounded w-1/2" />
                          </div>
                          <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center">
                            <div className="w-2 h-2 rounded-full bg-green-500" />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="text-center mt-6">
                  <p className="font-semibold">Team Collaboration</p>
                  <p className="text-sm text-muted-foreground">Work together seamlessly</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
